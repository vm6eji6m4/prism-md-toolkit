# PRISM MD Toolkit — LLM Knowledge Packaging Protocol

> Make AI read your project the same way humans do: **map first, details on demand.**
>
> **[繁體中文完整版 → README.zh-TW.md](README.zh-TW.md)**

Turn chaotic folders, papers, and codebases into **prioritized, navigable, auditable Markdown knowledge packs** for LLM consumption. One rule runs through every tool, learned from a real production incident: **convert to Markdown only what humans and LLMs read; never touch what programs read.**

| Tool | One-liner | Deps |
|---|---|---|
| [`prism/`](prism/) **PRISM packer** | Any folder → star-prioritized navigation pack + manifest (per-file sha256 / tokens / priority / AI summary) | PyMuPDF; tiktoken optional |
| [`prism/run_pipeline.py`](prism/run_pipeline.py) **Paper pipeline** | Paper/patent PDF → section slices → navigation pack + hybrid pack (core sections embedded in full); 5-corpus eval in [docs/PAPER_PIPELINE_EVAL.md](docs/PAPER_PIPELINE_EVAL.md) | same |
| [`tools/code_api_map.py`](tools/code_api_map.py) **Code API Map** | Python project → portable AST skeleton map (md + sqlite), ~80% token savings for agents without MCP tooling | stdlib only |
| [`tools/txt2md_copy.py`](tools/txt2md_copy.py) **Safe TXT→MD** | .txt corpus → .md copies with provenance headers; **never mutates originals** | stdlib only |

## Quickstart

```bash
pip install -r requirements.txt   # PyMuPDF only (see license note below)

# 1) Paper → navigation pack (--hybrid embeds core sections in full)
python prism/run_pipeline.py paper.pdf --hybrid

# 2) Whole folder → pack (-s index only; -o output dir, default cwd; GUI needs explicit --gui)
python prism/prism_pack.py <SOURCE_DIR> -o <OUT_DIR>

# 3) Python project → API map (output refused inside source tree)
python tools/code_api_map.py <PROJECT_DIR> -o API_MAP.md --db api.db

# 4) TXT corpus → MD knowledge copies (dry-run by default, --run to write)
python tools/txt2md_copy.py <SRC_DIR> <OUT_DIR> --run
```

## Safety by Design

A predecessor of these tools once renamed 4,000+ `.txt` files **in place** across an entire
drive — breaking tokenizers (`merges.txt`), `requirements.txt`, and build files (everything
was recovered from pre-conversion backups). Every tool now ships hard gates:

- **Never modify in place** — output goes to an explicit path outside the source tree; in-tree output is refused (exit 1)
- **Drive roots refused as source**
- **Dry-run by default**; writing requires explicit `--run`
- Every converted file carries a `# original-filename` provenance header → verifiable, precisely reversible
- Path gates use `realpath + normcase + commonpath` (symlink / UNC / case / string-prefix bypasses closed)

All gates are covered by **negative-control tests** (proving they actually refuse):
`python -m unittest discover tests` — 10 stdlib-only cases, green on Python 3.11/3.14.

## Star priority (PRISM)

`★★★★★` README/Abstract/entry points → `★★★★☆` sub-module docs/configs → `★★★☆☆` core code →
`★★☆☆☆` utilities → `★☆☆☆☆` tests/references. Hybrid packs embed ★★★★☆+ in full, index the rest.

## Verified numbers

- 1,385-file workspace (~1.69M est. tokens) → 3 md parts + manifest; a reviewer completed a full audit from the manifest alone
- Real project tree: 47 modules / 183 functions → 21KB API map (~5.3k tokens)
- Table-pollution guard: 5.8MB survey paper slices 45 → 16, zero real sections lost
- Corrupt-PDF negative control: fails immediately with `FileDataError`, no fake output

Reviewed by three independent AI reviewers (grades A- / B+ / per-question verdicts) before release — full audit trail (in Chinese, kept verbatim as historical record): [docs/REVIEW_VERDICT_20260717.md](docs/REVIEW_VERDICT_20260717.md)

## License

MIT (see [LICENSE](LICENSE); non-official Chinese reference translation: [docs/LICENSE.zh-TW.md](docs/LICENSE.zh-TW.md)).

⚠️ Dependency note: **PyMuPDF is AGPL-3.0** (commercial licenses sold by Artifex). This repo's own code is MIT and does not bundle PyMuPDF; if you redistribute a combined/commercial build, evaluate AGPL obligations or swap in a permissive PDF backend (e.g. pypdfium2).

## Provenance

Initial drafts by an execution agent (Antigravity) · verified, bug-fixed and hardened by a review agent (Claude) · product owner: [vm6eji6m4](https://github.com/vm6eji6m4) (Guoyu).
