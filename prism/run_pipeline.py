import sys
import shutil
from pathlib import Path

import prism_pack
import extractor
import splitter

# Priority threshold: sections with priority number <= this value get full content embedded
HYBRID_PRIORITY_THRESHOLD = 4  # ★★★★☆ and above

def custom_paper_priority(file_path: Path, sources: list[Path] = None) -> tuple[int, str]:
    name_upper = file_path.name.upper()
    
    if "ABSTRACT" in name_upper or "摘要" in name_upper:
        return (1, "★★★★★ (Core Architecture)")
    elif any(k in name_upper for k in ("METHODOLOGY", "METHOD", "ARCHITECTURE", "研究方法", "系統架構")):
        return (2, "★★★★★ (Main Entry Point)")
    elif any(k in name_upper for k in ("EXPERIMENT", "EVALUATION", "實驗", "評估")):
        return (4, "★★★★☆ (Sub-module Doc)")
    elif any(k in name_upper for k in ("RESULT", "DISCUSSION", "結果", "討論")):
        return (3, "★★★★☆ (Config & Settings)")
    elif any(k in name_upper for k in ("INTRODUCTION", "RELATED_WORK", "緒論", "文獻探討")):
        return (5, "★★★☆☆ (Core Code)")
    elif any(k in name_upper for k in ("APPENDIX", "附錄")):
        return (6, "★★☆☆☆ (Utility)")
    elif any(k in name_upper for k in ("REFERENCE", "BIBLIOGRAPHY", "參考文獻")):
        return (7, "★☆☆☆☆ (Test/Example)")
        
    return (5, "★★★☆☆ (Core Code)")

def build_hybrid_pack(lkp_summary_path: Path, slices_dir: Path, output_path: Path):
    """
    Build a hybrid pack that combines:
    1. The full LKP summary index (global map)
    2. Full raw content of top-priority sections (critical details)
    """
    summary_content = lkp_summary_path.read_text(encoding="utf-8")
    
    slice_files = sorted(slices_dir.glob("*.md"))
    prioritized = []
    for sf in slice_files:
        prio_num, prio_label = custom_paper_priority(sf)
        prioritized.append((prio_num, prio_label, sf))
    
    prioritized.sort(key=lambda x: x[0])
    
    embed_sections = [(p, label, f) for p, label, f in prioritized if p <= HYBRID_PRIORITY_THRESHOLD]
    skip_sections = [(p, label, f) for p, label, f in prioritized if p > HYBRID_PRIORITY_THRESHOLD]
    
    lines = []
    lines.append(summary_content.rstrip())
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 📖 Core Sections — Full Content (核心章節完整內文)")
    lines.append("")
    lines.append("> [!IMPORTANT]")
    lines.append("> **Hybrid Reading Strategy (混合閱讀策略)**:")
    lines.append(f"> The following {len(embed_sections)} sections are the most important (★★★★☆ and above).")
    lines.append("> Their **full original text** is embedded below for immediate deep reading.")
    if skip_sections:
        lines.append(f"> The remaining {len(skip_sections)} lower-priority sections are indexed above but NOT embedded.")
        lines.append("> If you need them, request the specific section file by its ID from the index table.")
    lines.append("")
    
    total_embedded_tokens = 0
    for prio_num, prio_label, sf in embed_sections:
        content = sf.read_text(encoding="utf-8")
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                content = parts[2].strip()
        
        # len//4 是英文換算率，中文會低估 3-4 倍 → 改用 prism_pack 的估算器（tiktoken 優先、CJK 感知 fallback）
        est_tokens = prism_pack.estimate_tokens(content)
        total_embedded_tokens += est_tokens
        
        lines.append(f"### 📄 {sf.name} `{prio_label}`")
        lines.append("")
        lines.append(f"<section name=\"{sf.stem}\" priority=\"{prio_label}\" est_tokens=\"{est_tokens}\">")
        lines.append("")
        lines.append(content)
        lines.append("")
        lines.append("</section>")
        lines.append("")
    
    if skip_sections:
        lines.append("---")
        lines.append("")
        lines.append("## ⏭️ Sections NOT Embedded (未嵌入的章節)")
        lines.append("")
        lines.append("| Section File | Priority | Reason |")
        lines.append("|:---|:---|:---|")
        for prio_num, prio_label, sf in skip_sections:
            lines.append(f"| {sf.name} | {prio_label} | Lower priority — available on request |")
        lines.append("")
    
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return len(embed_sections), len(skip_sections), total_embedded_tokens

def run_paper_pipeline(pdf_path: Path, hybrid: bool = False):
    if not pdf_path.exists():
        print(f"錯誤：找不到 PDF 檔案 {pdf_path}")
        return
        
    base_dir = pdf_path.parent
    paper_name = pdf_path.stem
    slices_dir = base_dir / f"{paper_name}_slices"
    
    if slices_dir.exists():
        shutil.rmtree(slices_dir)
    slices_dir.mkdir(parents=True, exist_ok=True)
    
    print("\n--- [Stage 1: 提取 PDF 文字] ---")
    markdown_content = extractor.extract_pdf_to_markdown(pdf_path)
    temp_md_path = base_dir / f"{paper_name}_temp.md"
    temp_md_path.write_text(markdown_content, encoding="utf-8")
    
    print("\n--- [Stage 2: 進行學術章節切片] ---")
    split_files = splitter.split_markdown_paper(temp_md_path, slices_dir)
    print(f"已切分出 {len(split_files)} 個章節 Markdown 檔案，存放於 {slices_dir}")
    
    if temp_md_path.exists():
        temp_md_path.unlink()
        
    print("\n--- [Stage 3: 呼叫 PRISM 封裝成導航包] ---")
    prism_pack.get_file_priority = custom_paper_priority
    
    lkp_output_path = base_dir / f"packaged_{paper_name}_summary.md"
    
    parts = prism_pack.run_pack_logic(
        sources=[slices_dir],
        out_file_path=lkp_output_path,
        chunk_limit=500000,
        max_size_kb=500,
        lite_mode=False,
        summary_only=True,
        log_callback=print,
        progress_callback=None
    )
    print(f"\n================ 摘要導航包完成！ ================")
    print(f"學術導航 Markdown 產出：{lkp_output_path}")
    
    if hybrid:
        print("\n--- [Stage 4: 建立混合模式包 (全局地圖 + 核心原文)] ---")
        hybrid_output_path = base_dir / f"packaged_{paper_name}_hybrid.md"
        n_embed, n_skip, est_tokens = build_hybrid_pack(lkp_output_path, slices_dir, hybrid_output_path)
        print(f"混合包產出：{hybrid_output_path}")
        print(f"  嵌入核心章節數：{n_embed} 個 (含完整原文)")
        print(f"  僅索引章節數：{n_skip} 個 (按需取件)")
        print(f"  核心章節預估 Token：~{est_tokens:,}")
    
    print(f"\n================ 全部任務順利完成！ ================")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_pipeline.py <pdf_path> [--hybrid]")
        sys.exit(1)
    
    pdf = Path(sys.argv[1])
    use_hybrid = "--hybrid" in sys.argv
    run_paper_pipeline(pdf, hybrid=use_hybrid)
