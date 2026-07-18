"""PRISM --skill mode: emit an Agent Skills compatible knowledge pack.

Output layout (open standard: https://agentskills.io):

    <corpus>-skill/
    ├── SKILL.md          # reading rules + Reading Ledger spec + star map
    ├── references/       # corpus files, rank-prefixed, flattened
    └── manifest.json     # sha256 / tokens / level per file (audit layer)

Design rulings (external review round 9, 1150718-2):
- Rules are *guidance*, not enforcement — the format raises compliance
  probability; hard enforcement only exists at a serving-protocol gate.
- No magic numbers: "open the minimum files needed", N is an optional
  parameter (strict default only in the evidence template).
- frontmatter uses standard fields only (name + description).
- Reading Ledger format is fixed — it is the product's audit moat.
"""

import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

from prism_pack import (
    EXCLUDE_EXTS,
    EXCLUDE_DIRS,
    calculate_sha256,
    clean_content,
    estimate_tokens,
    generate_auto_summary,
    get_file_priority,
    is_text_file,
    is_within,
)
import os

SKILL_BODY_TOKEN_BUDGET = 5000  # agentskills.io recommends SKILL.md body <= 5k tokens

# priority_val (0-7, from get_file_priority) -> semantic reading level
SEMANTIC_LEVELS = {
    0: "required", 1: "required", 2: "required",
    3: "important", 4: "important",
    5: "optional",
    6: "reference",
    7: "archive",
}

# Pre-pack secret scan (regex family only — CI-grade scanning belongs to
# Secretlint / GitHub secret scanning, this is a last-line local guard).
SECRET_PATTERNS = [
    ("anthropic-key", re.compile(r"sk-ant-[A-Za-z0-9\-_]{16,}")),
    ("generic-secret-key", re.compile(r"\bsk-[A-Za-z0-9]{24,}\b")),
    ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("github-pat", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b")),
    ("huggingface-token", re.compile(r"\bhf_[A-Za-z0-9]{20,}\b")),
    ("aws-key-id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("slack-token", re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{10,}\b")),
    ("google-api-key", re.compile(r"\bAIza[0-9A-Za-z\-_]{30,}\b")),
    ("private-key-block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
]

RULES_COMMON = """1. Read this SKILL.md fully before anything else. Do NOT open reference files yet.
2. Check the Map: if the whole corpus comfortably fits your working budget, you may
   read it all; otherwise open only the **minimum files needed to answer**.
3. Before opening any file, state which files you will open and why (one line each).
4. When candidates are equally relevant, prefer the smaller file first
   (token counts are listed in the Map). Levels (required/important/...) describe
   corpus structure, NOT per-question relevance — pick by relevance to the question.
5. If the answer is not in the corpus, say so explicitly ("not in the corpus").
   Never fill gaps with background knowledge or inference beyond the files.
6. Every answer MUST end with a Reading Ledger (exact format in section 2).
7. The Ledger may list ONLY files whose content was actually provided to you in
   this conversation. Never claim to have read a file you only saw in the Map."""

RULES_TEMPLATES = {
    "qa": RULES_COMMON,
    "review": RULES_COMMON + """
7. Review scope: read the files under review plus their direct dependencies only.
8. List every area you did NOT review in the Reading Ledger ("Skipped").""",
    "evidence": RULES_COMMON + """
7. Evidence mode: every claim must cite an exact source as `path:line-range`.
   A claim you cannot pin to a line range must be reported as "not verifiable
   in the corpus" — do not soften, do not estimate.
8. Open at most {max_files} files unless you first justify why more are required.""",
}

LEDGER_SPEC = """Every answer ends with this block (fixed format — it is the audit record):

```markdown
### Reading Ledger
- Consulted: <n>/<total> files | Focus: <one-line reason>
- Read:
  - <reference file> (<level>, <tokens> tokens) — <why>
- Skipped but relevant: <file> — <why skipped>  (omit line if none)
- Sources: <original path>:<line-range> — <claim it supports>  (one per claim)
- Self-check: hallucination risk <low|medium|high> — <basis, e.g. "all claims sourced">
```"""


def verify_ledger(answer_text: str, served_files: list[str]):
    """Machine-check a Reading Ledger against the actual serving record.

    Returns {"claimed": [...], "fabricated": [...], "ledger_present": bool}.
    Rationale (A/B retest 2026-07-18): a single-shot small model fabricated
    per-question ledger entries claiming files it was never served — the audit
    layer is only trustworthy when cross-checked against the serving protocol
    record, never when taken from the model's own words.
    """
    served = {Path(s).name for s in served_files}
    claimed = set()
    for m in re.finditer(r"references/([0-9]{3}_[^\s|)`,]+)", answer_text):
        claimed.add(m.group(1))
    for m in re.finditer(r"\b([0-9]{3}_[A-Za-z0-9_.\-一-鿿（）]+\.\w+)", answer_text):
        claimed.add(m.group(1))
    fabricated = sorted(c for c in claimed if c not in served)
    return {
        "ledger_present": "Reading Ledger" in answer_text,
        "claimed": sorted(claimed),
        "fabricated": fabricated,
    }


def scan_secrets(text: str):
    """Return list of (pattern_name, match_snippet) found in text."""
    hits = []
    for name, rx in SECRET_PATTERNS:
        m = rx.search(text)
        if m:
            snippet = m.group(0)[:12] + "…"
            hits.append((name, snippet))
    return hits


def collect_files(src: Path, max_size_kb: int, log):
    files = []
    exclude_dirs_lower = {x.lower() for x in EXCLUDE_DIRS}
    for root, dirs, names in os.walk(src):
        dirs[:] = [d for d in dirs if d.lower() not in exclude_dirs_lower and not d.startswith(".")]
        for name in names:
            fp = Path(root) / name
            if fp.suffix.lower() in EXCLUDE_EXTS:
                continue
            if is_text_file(fp, max_size_kb):
                files.append(fp)
    return files


def build_skill(src_path: Path, out_dir: Path, template: str = "qa",
                max_files_evidence: int = 5, max_size_kb: int = 500, log=print):
    """Build an Agent Skills compatible pack. Returns the skill dir Path."""
    if template not in RULES_TEMPLATES:
        raise ValueError(f"unknown template '{template}' (choose: {', '.join(RULES_TEMPLATES)})")
    src_path = src_path.resolve()
    skill_dir = out_dir.resolve() / f"{src_path.name}-skill"
    if is_within(skill_dir, src_path):
        raise ValueError(f"refuse: output {skill_dir} is inside the source tree")

    files = collect_files(src_path, max_size_kb, log)
    if not files:
        raise ValueError("no packable text files found")

    # analyze + secret scan
    entries, excluded = [], []
    for fp in files:
        try:
            raw = fp.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        hits = scan_secrets(raw)
        rel = fp.relative_to(src_path).as_posix()
        if hits:
            excluded.append({"path": rel, "patterns": [n for n, _ in hits]})
            log(f"  ⚠ secret suspect — excluded from pack: {rel} ({', '.join(n for n, _ in hits)})")
            continue
        cleaned = clean_content(raw)
        pv, stars = get_file_priority(fp, [src_path])
        entries.append({
            "path": rel,
            "local": fp,
            "sha256": calculate_sha256(fp),
            "tokens": estimate_tokens(cleaned),
            "lines": len(cleaned.splitlines()),
            "level": SEMANTIC_LEVELS[pv],
            "priority_val": pv,
            "stars": stars,
            "summary": generate_auto_summary(fp, cleaned),
        })

    # rank: required first, small files first inside a level (rule 4 dogfooding)
    entries.sort(key=lambda e: (e["priority_val"], e["tokens"], e["path"].lower()))
    for idx, e in enumerate(entries, 1):
        flat = e["path"].replace("/", "__")
        e["id"] = f"{idx:03d}"
        e["ref"] = f"{idx:03d}_{e['level']}_{flat}"

    # write references/
    ref_dir = skill_dir / "references"
    if skill_dir.exists():
        shutil.rmtree(skill_dir)
    ref_dir.mkdir(parents=True)
    for e in entries:
        shutil.copyfile(e["local"], ref_dir / e["ref"])

    total_tokens = sum(e["tokens"] for e in entries)
    rules = RULES_TEMPLATES[template].replace("{max_files}", str(max_files_evidence))

    def map_rows(items):
        rows = ["| # | Reference file | Level | Tokens | Summary |",
                "|---|---|---|---|---|"]
        for e in items:
            rows.append(f"| {e['id']} | references/{e['ref']} | {e['level']} "
                        f"| {e['tokens']:,} | {e['summary']} |")
        return rows

    def render_body(items, truncated_note=""):
        parts = [
            f"# {src_path.name} — knowledge pack (PRISM skill format)",
            "",
            f"Corpus: {len(entries)} files, ~{total_tokens:,} tokens total. "
            f"Rules template: `{template}`. Integrity: `manifest.json` (sha256 per file).",
            "",
            "## 1. Reading rules",
            "",
            rules,
            "",
            "## 2. Reading Ledger (required output)",
            "",
            LEDGER_SPEC,
            "",
            "## 3. Map",
            "",
            "Levels: required → read for any non-trivial question · important → likely needed "
            "· optional → open on demand · reference/archive → rarely needed.",
            "",
        ]
        parts += map_rows(items)
        if truncated_note:
            parts += ["", truncated_note]
        return "\n".join(parts) + "\n"

    # keep SKILL.md body inside the 5k-token recommendation: truncate map if needed
    body = render_body(entries)
    shown = list(entries)
    if estimate_tokens(body) > SKILL_BODY_TOKEN_BUDGET:
        full_map = "\n".join(map_rows(entries)) + "\n"
        (ref_dir / "000_full_map.md").write_text(full_map, encoding="utf-8")
        while shown and estimate_tokens(render_body(shown)) > SKILL_BODY_TOKEN_BUDGET - 60:
            shown = shown[:-1]
        note = (f"> Map truncated to the top {len(shown)} of {len(entries)} files "
                f"(SKILL.md body budget). Full map: `references/000_full_map.md`.")
        body = render_body(shown, note)

    desc = (f"Knowledge pack for '{src_path.name}' ({len(entries)} files). Load when answering "
            f"questions about this corpus. Follow the reading rules, open only needed "
            f"reference files, and always end answers with a Reading Ledger.")
    frontmatter = "\n".join([
        "---",
        f"name: {re.sub(r'[^a-z0-9-]+', '-', src_path.name.lower()).strip('-') or 'knowledge'}-knowledge",
        f"description: {desc}",
        "---",
        "",
    ])
    (skill_dir / "SKILL.md").write_text(frontmatter + body, encoding="utf-8")

    manifest = {
        "generator": "prism --skill",
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": src_path.name,
        "template": template,
        "total_files": len(entries),
        "total_tokens": total_tokens,
        "excluded_secret_suspects": excluded,
        "files": [{k: e[k] for k in ("id", "ref", "path", "sha256", "tokens",
                                     "lines", "level", "stars", "summary")}
                  for e in entries],
    }
    (skill_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    log(f"skill pack written: {skill_dir} ({len(entries)} refs"
        f"{', ' + str(len(excluded)) + ' excluded as secret suspects' if excluded else ''})")
    return skill_dir


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    template = "qa"
    out_dir = Path(".")
    if "--template" in argv:
        i = argv.index("--template")
        template = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    for flag in ("-o", "--out"):
        if flag in argv:
            i = argv.index(flag)
            out_dir = Path(argv[i + 1])
            argv = argv[:i] + argv[i + 2:]
    if not argv:
        print("usage: python skill_pack.py <SOURCE_DIR> [-o OUT_DIR] [--template qa|review|evidence]")
        return 1
    src = Path(argv[0])
    if not src.exists():
        print(f"error: source '{src}' does not exist")
        return 1
    build_skill(src, out_dir, template=template)
    return 0


if __name__ == "__main__":
    sys.exit(main())
