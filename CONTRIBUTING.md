# Contributing

PRs welcome — especially on the documented weak spots (docs/KNOWN_ISSUES.md):
PDF layout handling (vertical CJK!), splitter heuristics, priority rules.

Ground rules:
1. **Never mutate source trees.** Every tool writes only to explicit output paths
   outside the input tree. New code must pass the safety-gate tests.
2. **Zero-dependency core.** `tools/` stays stdlib-only; `prism/` allows PyMuPDF
   (required) and tiktoken (optional). Argue in an issue before adding anything.
3. **Tests are stdlib unittest**: `python -m unittest discover tests` must be green
   on Python 3.11+. Every safety gate needs a negative control (prove it refuses).
4. Keep docs honest — failure modes belong in KNOWN_ISSUES.md, not under the rug.
