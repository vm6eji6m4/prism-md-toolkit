# 外審裁決書 R2 — README 產品面重寫（2026-07-17）

> 第一輪（程式碼/架構）裁決見 [REVIEW_VERDICT_20260717.md](REVIEW_VERDICT_20260717.md)。
> 本輪評審對象＝README 的產品呈現，非程式碼。評審材料：六份獨立意見（GPT×2、Grok×2、Gemini×2）。

## 評審給分

| 評審 | 給分 | 核心診斷 |
|---|---|---|
| GPT | 技術 9.5／行銷 5／第一印象 4 | 「站在作者角度寫，不是站在陌生工程師角度」；建議整篇重排而非修補 |
| GPT-2 | 技術 9／問題真實性 9／定位 6.5（重包裝後 8.5-9） | Origin story 比 Protocol 有力；警告「定位膨脹」，v1 鎖定為工具 |
| Grok | （直接交重寫稿） | 語氣收斂、結構表格化、Safety 濃縮 |
| Grok-2 | （技術深挖＋路線建議） | 推薦「先輕量開源」路線；列 v3.5-v5 演進藍圖 |
| Gemini | （直接交重寫稿） | 內部結案報告感太重；主打 local model deployment 定位 |
| Gemini-2 | （鼓勵＋整合提問） | 從實戰事故長出的安全閘＝最大本錢 |

## 共識（六家全數或多數同意）→ 已全部落地

1. **第一屏只有一個訊息**：標語改為 GPT-2 提出的 **"Give AI a map before giving it the details."**（原三句三個定位互相打架）
2. **品牌收斂為 PRISM**：H1 從 "PRISM MD Toolkit — LLM Knowledge Packaging Protocol" 改為 "PRISM"；四工具改稱 PRISM Pack／Paper Pipeline／API Map／TXT Import（GPT 第八點：五個名字＝品牌感弱）
3. **"Protocol" 從第一屏移除**（GPT ①＋GPT-2 定位膨脹警告；v1 就是工具，不是標準）
4. **四工具呈現為一個工具箱的四種能力**，不是四個獨立專案（GPT 第二點）
5. **安全事故故事後移**：從第二屏移到 Quick Start／Example 之後，改用 "We learned that lesson so you don't have to" 框架（GPT 第三點＋Grok 濃縮＋Gemini 重框）
6. **加 Before/After Example 與 ASCII 流程圖**（GPT 第四、五點：Benefit 先於 Feature）
7. **Verified Numbers 改名 Benchmarks、改表格、後移**（GPT 第六點，比照 uv/ripgrep/duckdb）
8. **加 Origin/Philosophy 段**：TXT→MD 小實驗 → 發現真正瓶頸是導航不是格式；More context vs **Better context**（GPT-2）
9. **加 Roadmap 段**：內容取自第一輪外審共識（拆單體／YAML 規則／plugin／llms.txt／CI+PyPI／直排 CJK），誠實列未完成
10. **中英兩版各自純語言、結構互為鏡像**（GPT 第七點）
11. **Local model deployment 作為明確使用場景**寫進 Why 段（Gemini）
12. **Provenance 保留但去分數化**：代理分工與評審軌跡留在 docs 連結，首頁不再曝內部評分細節（Gemini：內部結案報告感）

## 被否決的建議（附理由）

| 建議 | 來源 | 否決理由 |
|---|---|---|
| Quickstart 改 `python -m prism.run_pipeline` | Grok | **實測會壞**：`prism/`、`tools/` 無 `__init__.py`，非 package；照抄會讓使用者第一條命令就失敗。package 化併入 Roadmap「拆單體」一起做 |
| 副標保留 "LLM-Native Knowledge Packaging Protocol" | Gemini | 與 GPT＋GPT-2 兩家共識（Protocol 降級）相抵，2:1 少數意見；依外審紀律從多數 |
| 首屏 [Install][Quick Start][Documentation] 按鈕列 | GPT | GitHub 原生自動 TOC 已覆蓋；徒增維護點 |
| "Built by VM6eji6M4" 單行署名取代 Provenance | GPT 重寫稿 | 代理分工與三家評審軌跡是本 repo 的誠實性資產，保留段落但精簡 |
| 首頁放社群預覽圖（實圖非 ASCII） | GPT | 認同方向，列入待辦（1280×640 banner），不擋本輪 |

## 本輪變更

- `README.md` 全篇重寫（英文純版，GPT 排版骨架＋GPT-2 標語與 Origin＋Grok 語氣＋Gemini 定位）
- `README.zh-TW.md` 全篇重寫（中文鏡像，結構一致）
- GitHub repo description 同步改為新標語
- 程式碼零變動；`python -m unittest discover tests` 不受影響
