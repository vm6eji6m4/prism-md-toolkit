# 外審裁決書（2026-07-17）
> 評審：三家獨立 AI 顧問（GPT／Grok／Gemini），材料＝70KB 單檔評審包（REVIEW_BRIEF 八問＋全碼）。
> 紀律：多家共識否決我方防線時，認錯改方向不硬拗；本檔記錄「哪些防線被否決」與處置。

## 總評
- GPT：**A-**（Originality 9.8／Security 9.4；「真正的產品是 LLM Knowledge Packaging Protocol，不是 Markdown 工具」）
- Grok：**B+ / 8.2**（OSS：可行；SaaS：潛力高但需重構）
- Gemini：逐題裁決（見下）＋上架前必改 TOP3

## 八問裁決（共識）
| 問 | 裁決 |
|---|---|
| Q1 三件合一 repo | **YES**（三家一致：完整的本地知識預處理管線） |
| Q2 CJK token 硬依賴 tiktoken | **NO**——維持輕量，校正係數即可（我方防線成立） |
| Q3 LLM 評星 | **NO**——過度工程（我方防線成立） |
| Q4 對齊 llms.txt | **YES**——降低攝取摩擦（列 roadmap） |
| Q5 安全閘是否足夠 | **❌ 我方防線被否決**：`.startswith()` 字串比對擋不住 symlink／UNC（`\\localhost\c$`）／大小寫繞過 |
| Q6 事故敘事入 README | **YES，大加分**（Postmortem-driven engineering） |
| Q7 差異化足以立足 | **YES**（星等＋混合包＋溯源頭＋安全閘） |
| Q8 直排 CJK | **UNKNOWN→條件式**：若訓文是硬需求，PyMuPDF text direction API 判向＝最高 ROI；OCR 過重 |

## 上架前必改 TOP3（已全數執行並以測試固化）
1. **路徑安全閘升級**（Q5 敗訴的處置）：三支工具統一改 `realpath＋normcase＋commonpath` 層級判定
   ——封 symlink／UNC／大小寫／前綴字串（`D:\a` vs `D:\ab`）四型繞過。
2. **無參數行為**：改印 usage＋exit 1；GUI 需顯式 `--gui`；tkinter 改懶載入（headless 連 import 都不再炸）。
3. **表格污染防線**：splitter 加標題字母/數字密度判定。回歸實測：llm_survey **45→16 片**
   （29 片表格垃圾清除、真章節零損失）；derived_geometry 11→10（消失的 1 片＝引用殘渣，應除）。

配套：`tests/test_toolkit.py` 10 條零依賴 unittest（3.11／3.14 雙綠），每道閘含負對照。

## 我方被否決並認列的防線
- 「負對照實測通過＝安全閘足夠」：**不成立**。負對照只證明「正常繞法會被擋」，
  沒證明「攻擊繞法會被擋」（symlink/UNC/大小寫）。教訓：安全閘驗證要含攻擊情境枚舉。

## 共識 Roadmap（上架後，依序）
- **P1**：拆 `prism_pack.py` 單體（core/cli/gui）；星等規則外部化（YAML）；logging 取代 print
- **P2**：Extractor/Tokenizer/Summary 插件化；llms.txt 對齊；GitHub Actions CI；PyPI
- **P3**：直排 CJK（PyMuPDF 判向）；定位語言全面轉「Knowledge Packaging Protocol」
- 商業化：Gemini 主張純 Web SaaS 不合適（本地機密不上雲）→ VS Code 擴充/CLI Pro 模式較合理；GPT 主張 OSS→Desktop→Cloud 四階段。**共識：先 OSS 建社群，商業化不急。**
