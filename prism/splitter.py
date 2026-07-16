import re
import sys
from pathlib import Path

# Common academic section headings in English and Chinese
ACADEMIC_SECTIONS = [
    (r"\babstract\b", "Abstract", "摘要"),
    (r"\bintroduction\b|\b緒論\b|\b前言\b", "Introduction", "緒論"),
    (r"\brelated\s+work\b|\bliterature\s+review\b|\b文獻探討\b", "Related_Work", "文獻探討"),
    (r"\bmethodology\b|\bmethod\b|\barchitecture\b|\b研究方法\b|\b系統架構\b", "Methodology", "研究方法"),
    (r"\bexperiment\b|\bevaluation\b|\b實驗\b|\b評估\b", "Experiments", "實驗與評估"),
    (r"\bresult\b|\bdiscussion\b|\b結果\b|\b討論\b", "Results", "結果與討論"),
    (r"\bconclusion\b|\b結論\b", "Conclusion", "結論"),
    (r"\breference\b|\bbibliography\b|\b參考文獻\b", "References", "參考文獻"),
    (r"\bappendix\b|\b附錄\b", "Appendix", "附錄")
]

def clean_filename(name: str) -> str:
    # Keep alphanumeric and underscore
    name = re.sub(r"[^\w\s-]", "", name).strip().replace(" ", "_")
    return name[:30]

def looks_like_real_heading(text: str) -> bool:
    """表格列誤判防線（2026-07-17 外審共識 TOP3）。

    extractor 會把 PDF 中粗體短行升格成 '##' 標題，綜述論文的表格列
    （如 '1024 TPU v3'）因此被誤切成章節。真標題應以字母/中文為主體：
    數字或符號密度過高者視為表格/資料列，併回所屬章節不另起切片。
    """
    t = text.strip()
    if not t or len(t) > 80:
        return False
    core = t.replace(" ", "")
    alpha = sum(c.isalpha() for c in core)
    digit = sum(c.isdigit() for c in core)
    return alpha / len(core) >= 0.55 and digit / len(core) <= 0.30

def split_markdown_paper(md_path: Path, output_dir: Path) -> list[Path]:
    """
    Splits a single Markdown paper file into multiple section files based on headings.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    content = md_path.read_text(encoding="utf-8")
    
    # Split content by markdown headings (lines starting with # or ##)
    lines = content.split("\n")
    
    current_section_name = "Header_Info"
    current_section_lines = []
    sections = []
    section_counter = 1
    
    def save_section(name, lines_list):
        nonlocal section_counter
        if not lines_list or not "".join(lines_list).strip():
            return
        
        # Determine clean filename
        prefix = f"{section_counter:02d}"
        filename = f"{prefix}_{clean_filename(name)}.md"
        filepath = output_dir / filename
        
        # Add metadata banner inside each section
        banner = f"---\ntype: paper_section\nsection_name: {name}\n---\n\n"
        filepath.write_text(banner + "\n".join(lines_list), encoding="utf-8")
        sections.append(filepath)
        section_counter += 1

    for line in lines:
        stripped = line.strip()
        is_heading = False
        heading_text = ""
        
        # Check if line is a markdown heading
        if stripped.startswith("#"):
            # Match # or ## or ###
            match = re.match(r"^#+\s+(.*)", stripped)
            if match and looks_like_real_heading(match.group(1)):
                is_heading = True
                heading_text = match.group(1).strip()
        else:
            # Check if line exactly matches a common section (heuristics for non-markdown text)
            for pattern, eng_name, ch_name in ACADEMIC_SECTIONS:
                if re.match(r"^" + pattern + r"\s*$", stripped, re.IGNORECASE):
                    is_heading = True
                    heading_text = stripped
                    break
        
        if is_heading:
            # Save the previous section
            save_section(current_section_name, current_section_lines)
            # Identify the new section name
            matched_name = None
            for pattern, eng_name, ch_name in ACADEMIC_SECTIONS:
                if re.search(pattern, heading_text, re.IGNORECASE):
                    matched_name = eng_name
                    break
            
            current_section_name = matched_name if matched_name else heading_text
            current_section_lines = [line]
        else:
            current_section_lines.append(line)
            
    # Save the last section
    save_section(current_section_name, current_section_lines)
    return sections

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python splitter.py <markdown_path> <output_dir>")
        sys.exit(1)
    md_file = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    split_files = split_markdown_paper(md_file, out_dir)
    print(f"切片完成！共切分為 {len(split_files)} 個章節檔案，存放於 {out_dir}")
