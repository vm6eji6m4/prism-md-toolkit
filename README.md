# PRISM

> **Give AI a map before giving it the details.**

Stop dumping thousands of files into an LLM and hoping. PRISM turns folders, papers, and codebases into **structured, prioritized knowledge packs** that AI navigates the way an experienced developer reads a new project — map first, details on demand.

**[繁體中文 → README.zh-TW.md](README.zh-TW.md)**

```
Repository · Papers · TXT corpus
              │
              ▼
            PRISM
              │
              ▼
Knowledge pack (map + manifest + prioritized content)
              │
              ▼
 Claude · GPT · Gemini · Cursor · local models
```

## Why PRISM?

LLMs don't fail on large projects because they can't read. They fail because nobody tells them **which files matter first**. Feed a 3,000-file repo raw and you get context overflow, blind sampling, and hallucinated architecture.

A human engineer never reads a project file-by-file:

```
README → architecture → entry points → core logic → details only when needed
```

PRISM packages that exact reading order for AI: a project map, star-priority ranking, per-file summaries, and an auditable manifest. In our 12-cell A/B evaluation this lifted answer accuracy from 6.5 to 8 of 8 with correct source attribution on a 45-file repo — **the map saves errors, not tokens**. (The honest exception: local single-shot models also need harness-side serving help — see the eval.)

## Features

Five capabilities, one toolkit:

### 📦 PRISM Pack — package any folder

Whole repository → star-prioritized navigation pack + manifest (sha256 / token estimate / priority / summary per file). Streaming output — 10k+ file trees won't exhaust memory. Does the map actually help? Honest 12-cell A/B evaluation (3 models × 2 corpora, traps as negative controls): [docs/MAP_VALUE_EVAL.md](docs/MAP_VALUE_EVAL.md).

### 🎓 PRISM Skill Pack — `--skill` mode

Any folder → an [Agent Skills](https://agentskills.io) compatible pack: `SKILL.md` (reading rules + Reading Ledger spec + star map) + smallest-first ranked `references/` + sha256 manifest. Rules are guidance, not enforcement — so `verify_ledger()` machine-checks every ledger claim against what was actually served (in our retest it caught a small model claiming to have read 5 files it was never given).

### 📄 PRISM Paper Pipeline — package papers & patents

PDF → section slices → navigation pack; `--hybrid` embeds the core sections in full. A table-pollution guard keeps giant survey tables from shredding the section splitter. Honest 5-corpus evaluation: [docs/PAPER_PIPELINE_EVAL.md](docs/PAPER_PIPELINE_EVAL.md).

### 🌳 PRISM API Map — package a codebase's skeleton

Python project → deterministic AST skeleton map (Markdown + SQLite), stdlib only. Hand it to any web LLM or agent without repo access: ~80% fewer tokens than shipping source.

### 📝 PRISM TXT Import — convert corpora safely

`.txt` corpus → `.md` copies with provenance headers. Never mutates originals. Dry-run by default.

## Quick Start

```bash
pip install -r requirements.txt   # PyMuPDF only (see license note below)

# Package a folder
python prism/prism_pack.py <SOURCE_DIR> -o <OUT_DIR>

# Package as an Agent Skills compatible pack (rules + Reading Ledger + map)
python prism/prism_pack.py <SOURCE_DIR> --skill -o <OUT_DIR> --template qa

# Package a paper (--hybrid embeds core sections in full)
python prism/run_pipeline.py paper.pdf --hybrid

# Map a Python project's API
python tools/code_api_map.py <PROJECT_DIR> -o API_MAP.md --db api.db

# Convert a TXT corpus (dry-run by default; --run to write)
python tools/txt2md_copy.py <SRC_DIR> <OUT_DIR> --run
```

## Example

Before — what the LLM sees:

```
my_project/                    1,385 files · ~1.69M tokens
├── src/ …
├── docs/ …
└── tests/ …
```

After `python prism/prism_pack.py my_project -o pack/`:

```
pack/
├── packaged_output.md         # the map: stats, tree, priority table, summaries
├── packaged_output_part2.md   # content, highest priority first
├── packaged_output_part3.md
└── manifest                   # sha256 / tokens / priority per file
```

In our own release audit, a reviewer completed a full workspace review **from the manifest alone**.

## Safety by Design

A predecessor of this toolkit once renamed 4,000+ `.txt` files **in place** across an entire drive — breaking tokenizers (`merges.txt`), `requirements.txt`, and build files (everything was recovered from pre-conversion backups). We learned that lesson so you don't have to. Every tool now ships hard gates:

- **Never modifies in place** — output must be an explicit path outside the source tree; in-tree output is refused (exit 1)
- **Drive roots refused** as source
- **Dry-run by default** — writing requires explicit `--run`
- Every converted file carries a `# original-filename` provenance header → verifiable, precisely reversible
- Path gates use `realpath + normcase + commonpath` (symlink / UNC / case / string-prefix bypasses closed)
- **Pre-pack secret scan** (`--skill` mode) — files matching credential patterns (API keys, tokens, private keys) are excluded from the pack and recorded in the manifest

All gates are covered by **negative-control tests** (proving they actually refuse):
`python -m unittest discover tests` — 20 stdlib-only cases, green on Python 3.11/3.14.

## Benchmarks

| Scenario | Result |
|---|---|
| 12-cell map-value A/B (3 models × 2 corpora) | on a 45-file repo the map lifted accuracy 6.5 → 8 of 8 with correct sources — at ~24% **more** tokens. The map saves errors, not tokens ([details](docs/MAP_VALUE_EVAL.md)) |
| 1,385-file workspace (~1.69M est. tokens) | 3 md parts + manifest; full audit completed from manifest alone |
| Python project, 47 modules / 183 functions | 21 KB API map (~5.3k tokens) |
| 5.8 MB survey paper with heavy tables | slices 45 → 16, zero real sections lost |
| Corrupt PDF | immediate `FileDataError`, no fake output |

## Philosophy

PRISM started as a small experiment: "Markdown reads better than TXT, and saves tokens." Real use exposed the deeper problem — the bottleneck isn't file format, it's that **AI doesn't know where to start reading**. Most AI tooling chases *more* context (bigger windows, RAG, embeddings); PRISM chases **better** context: navigation before retrieval, the map before the details.

One rule runs through every tool, learned from the incident above: **convert to Markdown only what humans and LLMs read; never touch what programs read.**

## Roadmap

- [x] Folder packing · paper pipeline · API map · safe TXT import
- [x] `--skill` mode: Agent Skills compatible packs (reading rules + Reading Ledger + machine-checkable `verify_ledger()`)
- [ ] Harness-side smallest-first serving for local single-shot models (rules alone don't fix budget starvation — see MAP_VALUE_EVAL)
- [ ] Split the packer monolith (core / cli / gui)
- [ ] YAML-configurable priority rules + plugin hooks
- [ ] llms.txt export
- [ ] CI + PyPI packaging
- [ ] Vertical CJK PDF support (the hard one — see KNOWN_ISSUES)

Known limitations are documented honestly in [docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md). PRs welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT ([LICENSE](LICENSE); non-official Chinese reference translation: [docs/LICENSE.zh-TW.md](docs/LICENSE.zh-TW.md)).

⚠️ **PyMuPDF is AGPL-3.0** (commercial licenses sold by Artifex). This repo's own code is MIT and does not bundle PyMuPDF; if you redistribute a combined/commercial build, evaluate AGPL obligations or swap in a permissive PDF backend (e.g. pypdfium2).

## Provenance

Drafted by an execution agent, then verified, bug-fixed and hardened by a review agent; reviewed by three independent AI reviewers before release — condensed audit summary: [docs/AUDIT_LOG.md](docs/AUDIT_LOG.md). Product owner: [vm6eji6m4](https://github.com/vm6eji6m4) (Guoyu).
