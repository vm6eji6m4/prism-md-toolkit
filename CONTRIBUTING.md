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

---

## 中文版

歡迎 PR——尤其是已文件化的弱點（docs/KNOWN_ISSUES.md）：PDF 版面處理（直排中文！）、切片啟發式、星等規則。

基本規則：
1. **永不就地修改來源樹**。所有工具只寫明確指定的樹外輸出路徑；新碼必須通過安全閘測試。
2. **核心零依賴**。`tools/` 只用標準庫；`prism/` 允許 PyMuPDF（必要）與 tiktoken（選配）。要加東西先開 issue 討論。
3. **測試用標準庫 unittest**：`python -m unittest discover tests` 在 Python 3.11+ 必須全綠。每道安全閘都要有負對照（證明它真的會拒絕）。
4. 文件要誠實——失敗模式寫進 KNOWN_ISSUES.md，不准掃地毯下。
