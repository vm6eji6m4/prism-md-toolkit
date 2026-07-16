# 外部評審簡報（REVIEW BRIEF）— PRISM MD Toolkit
> 2026-07-17 · 出題：國裕（產品負責）＋ Claude（審核代理）· 目標：收斂「加強清單」後上架 GitHub
> 評審請直接批判，不需客氣；我們的紀律是「多家共識否決我方防線時，認錯改方向不硬拗」。

## 1. 這是什麼

三件 MD-native 知識封裝工具（詳見 README）：
1. **PRISM**：資料夾/PDF → 星等分級導航包＋manifest＋混合包
2. **code_api_map**：Python 專案 → AST 骨架地圖（md+sqlite），給無工具環境的 LLM/委外代理
3. **txt2md_copy**：txt 素材 → 帶溯源頭 md 副本（複製式，永不動原檔）

使用場景：獨立開發者的「可稽核外部大腦」——本地檔案系統＝AI 長期記憶，
Obsidian 雙鏈＋LLM 打包互通；另用於多代理委外流程（BRIEF 包附 API 地圖給執行代理）。

## 2. 已驗證的部分（不用再驗）

- 全新環境重跑四階段管線通過；壞 PDF 負對照正確失敗
- code_api_map 對賬（模組/類別/函數計數 vs sqlite vs md 輸出一致）；輸出禁寫來源樹閘門 exit=1
- txt2md_copy 三道安全閘負對照（樹內輸出/磁碟根來源/dry-run 預設）
- 實戰：1,385 檔工作區打包後，僅靠 manifest 完成全區審核

## 3. 已知弱點（誠實列出，附我方傾向）

| # | 弱點 | 我方傾向 |
|---|---|---|
| W1 | token 估算：tiktoken 缺席時 fallback `char*0.6+word*0.8`，**中文精度未 benchmark**；混合包舊版曾用 `len//4`（已修） | 做一次 CJK benchmark 校正係數即可，不引重依賴 |
| W2 | 星等優先權＝檔名/路徑關鍵字啟發式（`custom_paper_priority`），非內容理解 | 保持啟發式為預設（零成本、決定論），加可選 LLM 評星 hook |
| W3 | `prism_pack.py` 813 行單體，CLI 與 Tkinter GUI 耦合 | 拆 core/gui 兩模組，行為不變 |
| W4 | extractor 頁首尾過濾＝固定 8% 高度啟發式；雙欄/浮動版面會漏 | 已知取捨，文件註明；不追求完美 PDF 解析 |
| W5 | code_api_map 只有骨架（模組/類/函數/簽名/docstring），**無呼叫邊**（call graph） | 維持輕量定位；呼叫邊屬 codegraph 級工具的職責 |
| W6 | txt2md fence 規則粗糙（>100 行或含 error/traceback 才包 ```text） | 可改成「非散文比率」偵測，或乾脆全包 fence |
| W7 | manifest schema 自定義，未對齊任何社群標準 | 想聽評審意見：有無值得對齊的 llms.txt / MCP resource 類慣例？ |
| W8 | ~~CLI 預設路徑寫死開發者個人資料夾~~（上架前狗糧測試抓到，**已修**：來源必填、`-o` 指定輸出、預設 cwd、輸出禁入來源樹） | 已閉環，列出供評審檢查修法 |
| W9 | 無參數時進 Tkinter GUI 模式——headless/CI 環境行為未定義 | 傾向加 `--gui` 顯式旗標，無參數改印 usage |
| W10 | 論文管線：綜述論文的**表格列被誤切成章節**（45 片約 3 成假章節，證據見 PAPER_PIPELINE_EVAL F1） | 切片前加表格密度偵測 |
| W11 | 論文管線：**直排 CJK 版面完全失敗**（12MB 直式中文手冊只出 1 片散字，F2）——主要目標場景（宗教訓文/傳統文書）的硬缺口 | bbox 判向改讀取順序，或降級 OCR |

## 4. 請評審回答的七個問題

1. **定位**：三件組合成一個 repo 是否成立？還是 PRISM 單獨上、其餘當 examples？
2. **W1**：CJK token 估算，校正係數 vs 引 tiktoken 為硬依賴 vs 其他輕量 tokenizer，怎麼選？
3. **W2**：星等交給 LLM 評的 ROI 值得嗎？（我們的原則：別過度工程）
4. **W7**：manifest 該不該對齊 `llms.txt` 或其他新興慣例？2026 年有無事實標準？
5. **安全閘**設計還有沒有漏洞？（歡迎想像攻擊情境：symlink、UNC 路徑、大小寫、junction…）
6. **README 的事故敘事**（safety by design 段）放公開 repo 是加分還是扣分？
7. 同類開源工具（repomix / gitingest / code2prompt 等）已存在，**本組差異化**（星等分級＋混合包＋溯源頭＋安全閘）足以立足嗎？還是該貢獻上游？
8. **W11 直排 CJK** 是我們目標場景（中文宗教訓文/傳統文書）的硬缺口：bbox 判向 vs 整頁 OCR 降級 vs 宣告不支援並文件註明，哪條路 ROI 最好？有無現成庫（如 PyMuPDF 4.x 的 text direction API）可借力？

## 5. 評審格式

照慣例：每題一行結論（YES/NO/UNKNOWN＋理由），最後給「上架前必改 TOP3」。
多家評審共識 > 我方防線；裁決書會記錄哪些防線被否決。
