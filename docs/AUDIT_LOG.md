# Audit Log

This project was independently reviewed before and after release. This file is the condensed public summary; the verbatim review records (in Chinese) are preserved in this repo's git history for anyone who wants the full trail.

## Round 1 — code & architecture (2026-07-17)

Three independent AI reviewers (GPT / Grok / Gemini) received a 70KB single-file pack of the entire codebase — built with PRISM itself — plus eight hard questions.

Key outcomes, fixed in commit `c3aaf47`:

1. **Path safety gates rewritten.** Our `.startswith()` string check was rejected: symlink, UNC, case, and `D:\a`-vs-`D:\ab` prefix bypasses all got through. All three tools now gate with `realpath + normcase + commonpath`. Lesson conceded: passing negative controls does not prove a security gate is sufficient — gates need attack-scenario enumeration.
2. **CLI hardening.** No-args prints usage and exits 1; the GUI requires an explicit `--gui`; tkinter is lazily imported (headless-safe).
3. **Splitter table-pollution guard.** A heading-density check cut a 5.8MB survey paper's slices from 45 to 16 with zero real sections lost.
4. **Tests.** 10 stdlib-only unittest cases added; every safety gate has a negative control proving it actually refuses.

## Round 2 — README & product presentation (2026-07-17)

Six review passes (GPT ×2, Grok ×2, Gemini ×2) converged: strong technical content, weak first impression. The README was rewritten (commit `8382603`): one first-screen message, brand collapsed to **PRISM**, safety story moved below Quick Start, Before/After example, Benchmarks table, honest Roadmap, and fully mirrored English/Chinese versions.

Reviewer suggestions rejected, with reasons:

- **`python -m prism.run_pipeline` invocation** — the packages have no `__init__.py`, so the copy-pasted command would fail. Deferred to the packaging roadmap item.
- **Keeping "Protocol" in the title** — v1 is a tool, not a standard; positioning stays locked until the tool earns it.

Surviving limitations are tracked in [KNOWN_ISSUES.md](KNOWN_ISSUES.md); the paper-pipeline failure modes in [PAPER_PIPELINE_EVAL.md](PAPER_PIPELINE_EVAL.md).
