# PRISM MD Toolkit — LLM 知識封裝三件組
> Markdown-native knowledge packaging for LLM consumption: bundle anything → prioritized, navigable, auditable MD.

把「一整包混沌資料」變成 **LLM 最佳閱讀路徑**的三件工具。共同哲學：**先給地圖、再按需取件**（Progressive Disclosure），以及一條用生產事故換來的鐵律——**給人和 LLM 讀的才轉 MD；給程式讀的永遠保持原格式**。

| 工具 | 一句話 | 依賴 |
|---|---|---|
| [`prism/`](prism/) **PRISM 封裝管線** | PDF/論文/整個專案資料夾 → 星等分級導航包＋manifest（每檔 sha256/tokens/星等/AI 摘要）＋混合包（核心章節嵌原文） | PyMuPDF；tiktoken 選配 |
| [`tools/code_api_map.py`](tools/code_api_map.py) **CODE API MAP** | Python 專案 → AST 決定論 API 骨架地圖（md＋sqlite），委外/網頁端 LLM 帶著走，實測省 ~80% token | 純標準庫 |
| [`tools/txt2md_copy.py`](tools/txt2md_copy.py) **TXT→MD 安全轉檔** | .txt 素材 → 帶溯源頭的 .md 副本，餵 Obsidian/RAG/打包器；**永不動原檔** | 純標準庫 |

## Quickstart

```bash
pip install -r requirements.txt   # 只有 PyMuPDF 必裝

# 1) 論文 → 導航包（--hybrid 加嵌核心章節原文）
python prism/run_pipeline.py paper.pdf --hybrid

# 2) 整個資料夾 → 打包（-s 只出索引；-o 指定輸出目錄，預設 cwd；無參數=Tkinter GUI）
python prism/prism_pack.py <SOURCE_DIR> -o <OUT_DIR>

# 3) Python 專案 → API 地圖（輸出禁寫來源樹）
python tools/code_api_map.py <PROJECT_DIR> -o API_MAP.md --db api.db

# 4) TXT 素材 → MD 知識庫副本（預設 dry-run，--run 才寫）
python tools/txt2md_copy.py <SRC_DIR> <OUT_DIR> --run
```

## 安全設計（Safety by Design）

這套工具的前身曾釀成真實事故：一支「就地改名」的 txt→md 轉檔器掃過整顆磁碟，改壞了
tokenizer（`merges.txt`）、`requirements.txt`、build 檔等 4,000+ 個「給程式讀的」檔案
（靠轉檔前的自動備份全數還原）。現版全部工具因此內建硬性安全閘：

- **永不就地修改**：一律複製到樹外輸出目錄；輸出路徑落在來源樹內 → 直接拒絕（exit 1）
- **拒收磁碟根**當來源（`src.parent == src` 判定）
- **預設 dry-run**，明確 `--run` 才落盤
- 每個轉出的 md 首行帶 `# 原檔名` 溯源頭 → 事後可簽名比對、可精確回滾
- 隱藏目錄（`.venv*`/`.git`…）與依賴目錄一律跳過

以上閘門均以**負對照**實測（餵壞輸入證明會正確失敗，不產假輸出）。

## 星等優先權（PRISM）

`★★★★★` README/Abstract/主入口 → `★★★★☆` 子模組文件/設定 → `★★★☆☆` 主代碼 →
`★★☆☆☆` 工具函式 → `★☆☆☆☆` 測試/參考文獻。混合包預設嵌入 ★★★★☆ 以上原文，其餘僅索引。

## 實測數字（驗收紀錄）

- 1,385 檔（1.69M est. tokens）工作區 → 3 個 md part＋manifest，審核者僅靠 manifest 聚合完成全區理解
- line-ollama-engine 全樹 47 模組/183 函數 → 21KB API 地圖（~5.3k tokens）
- 壞 PDF 負對照：`FileDataError` 立即失敗，零假輸出

## Provenance

Antigravity（執行代理）初版開發 · Claude（審核代理）親驗/修 bug/安全加固 · 國裕（vm6eji6m4）產品負責。
評審資料見 [docs/REVIEW_BRIEF.md](docs/REVIEW_BRIEF.md)、已知限制見 [docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md)。

MIT License.
