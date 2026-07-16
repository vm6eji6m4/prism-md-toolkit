# KNOWN ISSUES / 已知限制

> ✅ 2026-07-17 外審後已修：路徑安全閘（realpath 層級判定，封 symlink/UNC/大小寫）、
> 無參數＝GUI 的未定義行為（改印 usage，GUI 需 `--gui`，tkinter 懶載入）、
> 綜述論文表格列誤切（標題密度防線，45→16 片）。以下為仍存在的限制。

- **CJK token 估算精度未校正**：tiktoken 未安裝時 fallback `char*0.6 + word*0.8`；對純中文文本的誤差未 benchmark。混合包（run_pipeline）舊版用 `len//4`（中文低估 3-4 倍），本 repo 已改用統一估算器。
- **星等＝啟發式**：檔名/路徑關鍵字判定，重新命名檔案會改變星等；非內容理解。
- **extractor 版面假設**：固定過濾頁面上下 8% 當頁首尾；雙欄靠 block 座標排序，複雜版面（浮動圖表/三欄）會亂序。
- **splitter 章節偵測**：規則式（學術章節關鍵字），非學術文件切分品質下降。
- **code_api_map 無呼叫邊**：只有 API 骨架，不含 call graph/dataflow（設計取捨：那是 codegraph 級工具的職責）。
- **prism_pack 單體**：813 行含 Tkinter GUI，待拆分。
- **Windows 優先**：路徑安全閘以 Windows 語意實測；POSIX symlink/mount 情境未測。
- **txt2md fence 規則**：`>100 行或含 error/traceback` 才包 code fence，散文/資料混合檔判定粗糙。
- **輸出檔名固定 `packaged_skills.md`**：`-o` 只能指定目錄，不能改檔名（多來源打包會互相覆蓋）。
- **prism_pack 單體待拆**（core/cli/gui 分層＝外審共識 P1）；星等規則硬編待外部化（YAML）。
- **無結構化 logging**：目前 print 為主；錯誤處理有寬泛 `except Exception`。
- **記憶體**：目錄樹與 metadata 清單全載記憶體，百萬檔級 repo 有 O(N) 風險。
