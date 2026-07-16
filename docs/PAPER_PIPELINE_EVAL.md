# 論文開發器（Paper Pipeline）三語料實測報告
> 管線＝`prism/run_pipeline.py`（extractor → splitter → PRISM 封裝 → 混合包）。
> 語料為第三方 PDF 與內部文件，**不隨 repo 散布**；本檔記錄可重現的結果與失敗模式。
> 測試執行：Antigravity（2026-07-15）；判讀與失敗模式分析：Claude（2026-07-17）。

## 語料梯度與結果

| 語料 | 規模 | 類型 | 切片數 | 判定 |
|---|---|---|---|---|
| test_paper.pdf | 190KB | 會議模板（英） | 5 | ✅ 煙測基準，含負對照（壞 PDF 正確報錯） |
| derived_geometry.pdf | 0.9MB | 數學論文（英） | 11 | ✅ 章節切分正常（Introduction／History／Derived schemes…） |
| llm_survey.pdf | 5.8MB | 大型綜述（英，多表格） | 45 | ⚠️ 可用但污染：**表格列被誤切成章節**（如 `04_1024_TPU_v3.md`＝表格內容行） |
| hard_doc.pdf | 12.3MB | **直式排版中文手冊** | 1 | ❌ 完全失敗：直排字被逐字打散（「講／師／精／進」），無章節結構可切 |
| patent_test.pdf | 3.0MB | 專利文件 | 0 | ❓ 無輸出紀錄＝未完成測試，待補跑 |

## 失敗模式分析

### F1 表格污染（llm_survey）
splitter 以「短行＋標題樣式」啟發式判定章節邊界；綜述論文的寬表格經 extractor 攤平後，
表格列（`1024 TPU v3`、`2048 Ascend 910`…）樣式近似標題 → 45 片中約 3 成是假章節。
**影響**：星等分級與混合包嵌入會把垃圾片當內容。
**修法方向**：切片前加「表格密度」偵測（數字/分隔符比率），高密度區段整塊歸入所屬章節不再細切。

### F2 直排 CJK 版面（hard_doc）
extractor 依 block 座標「上→下、左→右」排序＝橫排假設；直排中文（右→左、上→下）
被讀成垂直散字，句子完全解體。
**影響**：**宗教訓文／傳統文書多為直排**——這是本工具箱在佛堂場景的主要缺口。
**修法方向**：PyMuPDF block bbox 可判向（高瘦 block 群＝直排）→ 偵測後改用直排讀取順序；
或該頁降級走 OCR。屬「值得做」級，優先度請外審表態（REVIEW_BRIEF Q8）。

## 重現方式

```bash
python prism/run_pipeline.py <你的PDF> --hybrid
# 檢查 <PDF名>_slices/ 的切片檔名是否出現表格內容；直排文件看 01_Header_Info.md 是否散字
```
