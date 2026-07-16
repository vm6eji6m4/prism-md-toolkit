# PRISM

> **先給 AI 地圖，再給它細節。**

別再把幾千個檔案硬塞給 LLM 然後祈禱。PRISM 把資料夾、論文、程式庫變成**結構化、有優先級的知識包**，讓 AI 用資深工程師讀新專案的方式導航——先看地圖，細節按需取件。

**[English → README.md](README.md)**

```
專案資料夾 · 論文 PDF · TXT 語料
              │
              ▼
            PRISM
              │
              ▼
 知識包（地圖 + manifest + 依優先級排序的內容）
              │
              ▼
 Claude · GPT · Gemini · Cursor · 本地模型
```

## 為什麼需要 PRISM？

LLM 面對大專案的失敗，不是因為讀不懂，而是**沒人告訴它先看哪裡**。3,000 個檔案原樣餵進去，得到的是 context 爆量、盲目抽讀、幻覺出來的架構。

人類工程師從不逐檔讀專案：

```
README → 架構 → 入口程式 → 核心邏輯 → 需要時才看細節
```

PRISM 把這套閱讀順序打包給 AI：專案地圖、星等排序、逐檔摘要、可稽核的 manifest——讓模型讀 5% 就理解 95%。對**本地模型部署**尤其重要：每一個 context token 都是成本。

## 功能

一個工具箱，四種能力：

### 📦 PRISM Pack — 打包任何資料夾

整個專案 → 星等分級導航包＋manifest（每檔 sha256／token 估計／星等／摘要）。串流寫出——上萬檔案的樹也不會爆記憶體。

### 📄 PRISM Paper Pipeline — 打包論文與專利

PDF → 章節切片 → 導航包；`--hybrid` 把核心章節全文嵌入。表格污染防線讓巨型綜述表格不會絞碎章節切割器。誠實的五語料測評：[docs/PAPER_PIPELINE_EVAL.md](docs/PAPER_PIPELINE_EVAL.md)。

### 🌳 PRISM API Map — 打包程式庫骨架

Python 專案 → 決定論 AST 骨架地圖（Markdown＋SQLite），純標準庫。交給沒有 repo 存取權的網頁版 LLM 或委外代理：比直接貼原始碼省約 80% token。

### 📝 PRISM TXT Import — 安全轉檔語料

`.txt` 語料 → 帶溯源頭的 `.md` 副本。永不動原檔，預設 dry-run。

## Quick Start

```bash
pip install -r requirements.txt   # 只有 PyMuPDF 必裝（授權注意見下方）

# 打包整個資料夾
python prism/prism_pack.py <來源資料夾> -o <輸出資料夾>

# 打包論文（--hybrid 嵌入核心章節全文）
python prism/run_pipeline.py paper.pdf --hybrid

# 產生 Python 專案 API 地圖
python tools/code_api_map.py <專案資料夾> -o API_MAP.md --db api.db

# TXT 語料轉檔（預設 dry-run；--run 才真的寫）
python tools/txt2md_copy.py <來源> <輸出> --run
```

## 範例

轉換前——LLM 看到的：

```
my_project/                    1,385 檔 · 約 169 萬 token
├── src/ …
├── docs/ …
└── tests/ …
```

跑完 `python prism/prism_pack.py my_project -o pack/`：

```
pack/
├── packaged_output.md         # 地圖：統計、目錄樹、優先級表、摘要
├── packaged_output_part2.md   # 內容，優先級高的排前面
├── packaged_output_part3.md
└── manifest                   # 每檔 sha256／tokens／星等
```

在我們自己的上架審核中，評審者**只靠 manifest 就完成了整個工作區的稽核**。

## 安全設計（Safety by Design）

這套工具的前身曾釀成真實事故：一支「就地改名」轉檔器掃過整顆磁碟，改壞了 tokenizer（`merges.txt`）、`requirements.txt`、build 檔等 4,000+ 個「給程式讀的」檔案（靠轉檔前的自動備份全數還原）。教訓我們吃過了，你不用再吃一次。現版所有工具內建硬性安全閘：

- **永不就地修改**——一律寫到來源樹以外的明確輸出路徑；輸出落在來源樹內 → 直接拒絕（exit 1）
- **拒收磁碟根**當來源
- **預設 dry-run**，明確 `--run` 才落盤
- 每個轉出檔首行帶 `# 原檔名` 溯源頭 → 可簽名比對、可精確回滾
- 路徑閘用 `realpath + normcase + commonpath`（symlink／UNC／大小寫／字串前綴繞過全部封死）

以上閘門全數有**負對照測試**（證明它真的會拒絕）：
`python -m unittest discover tests`——10 條零依賴測試，Python 3.11/3.14 雙版本全綠。

## 實測數字（Benchmarks）

| 場景 | 結果 |
|---|---|
| 1,385 檔工作區（約 169 萬 est. tokens） | 3 個 md part＋manifest；評審只靠 manifest 完成全區稽核 |
| Python 專案 47 模組／183 函數 | 21KB API 地圖（約 5.3k tokens） |
| 5.8MB 重表格綜述論文 | 切片 45 → 16，真章節零損失 |
| 壞 PDF | 立即 `FileDataError` 失敗，零假輸出 |

## 設計哲學

PRISM 一開始只是個小實驗：「MD 比 TXT 好讀，還順便省 token」。真實使用後才發現更深的問題——瓶頸不是檔案格式，是 **AI 不知道從哪裡開始讀**。多數 AI 工具在追「更多 context」（更大視窗、RAG、embedding）；PRISM 追的是「**更好的 context**」：先導航、後檢索；先地圖、後細節。

所有工具貫穿同一條用事故換來的鐵律：**給人和 LLM 讀的才轉 Markdown；給程式讀的永遠不碰。**

## Roadmap

- [x] 資料夾打包 · 論文管線 · API 地圖 · 安全 TXT 轉檔
- [ ] 拆分打包器單體（core／cli／gui）
- [ ] 星等規則 YAML 化＋plugin 掛鉤
- [ ] llms.txt 匯出
- [ ] CI＋PyPI 打包
- [ ] 直排中文 PDF 支援（最硬的一塊——見 KNOWN_ISSUES）

已知限制誠實記錄在 [docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md)。歡迎 PR——見 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 授權

MIT（正式文本＝英文 [LICENSE](LICENSE)；中文參考譯本與白話說明見 [docs/LICENSE.zh-TW.md](docs/LICENSE.zh-TW.md)）。

⚠️ 依賴注意：**PyMuPDF 是 AGPL-3.0**（Artifex 另售商業授權）。本 repo 自身程式碼為 MIT 且不打包 PyMuPDF；若日後要做閉源／商業散布版，需評估 AGPL 義務或改用寬鬆授權的 PDF 後端（如 pypdfium2）。

## Provenance

執行代理起草初版 → 審核代理親驗、修 bug、安全加固 → 上架前經三家獨立 AI 評審（完整稽核紀錄原文保留：[docs/REVIEW_VERDICT_20260717.md](docs/REVIEW_VERDICT_20260717.md)）。產品負責：[vm6eji6m4](https://github.com/vm6eji6m4)（國裕）。
