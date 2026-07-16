import sys
from pathlib import Path
import fitz  # PyMuPDF

def extract_pdf_to_markdown(pdf_path: Path) -> str:
    """
    Extracts text from PDF and converts it into a clean Markdown string.
    Filters out common header/footer noises.
    """
    print(f"正在讀取 PDF: {pdf_path.name}")
    doc = fitz.open(pdf_path)
    markdown_lines = []
    
    for page_idx, page in enumerate(doc):
        # Extract blocks of text
        blocks = page.get_text("blocks")
        # Sort blocks top-to-bottom, left-to-right to handle double columns if possible
        # Page height
        page_height = page.rect.height
        
        # Sort blocks: first by y-coordinate, then by x-coordinate
        # To avoid page headers/footers, we ignore blocks in the top 8% and bottom 8% of the page height
        valid_blocks = []
        for b in blocks:
            x0, y0, x1, y1, text, block_no, block_type = b
            # Ignore headers/footers
            if y0 < page_height * 0.08 or y1 > page_height * 0.92:
                continue
            valid_blocks.append(b)
            
        # Simple column sorter: if there is a lot of overlap in X coordinates, it might be double column.
        # For simplicity, we sort by y0 primarily, but if two blocks are side-by-side (y0 difference is small),
        # we sort by x0.
        valid_blocks.sort(key=lambda b: (round(b[1] / 10) * 10, b[0]))
        
        for b in valid_blocks:
            text = b[4].strip()
            if not text:
                continue
                
            # If the block looks like a heading (e.g. capitalized, short, starts with number)
            # We can format it nicely
            lines = text.split("\n")
            cleaned_block = []
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                # Heading detection heuristic (e.g. "1. Introduction" or "Abstract")
                import re
                if re.match(r"^(\d+\.?\d*)\s+[A-Z]", line) or line.upper() in ("ABSTRACT", "INTRODUCTION", "METHODOLOGY", "EXPERIMENTS", "RESULTS", "CONCLUSION", "REFERENCES"):
                    cleaned_block.append(f"\n## {line}\n")
                else:
                    cleaned_block.append(line)
            
            markdown_lines.append(" ".join(cleaned_block))
            
    full_text = "\n\n".join(markdown_lines)
    
    # Post-processing: clean up excessive line breaks and space
    # Replace multiple newlines with double newlines
    import re
    full_text = re.sub(r'\n{3,}', '\n\n', full_text)
    return full_text

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extractor.py <pdf_path>")
        sys.exit(1)
    pdf = Path(sys.argv[1])
    md_content = extract_pdf_to_markdown(pdf)
    out_md = pdf.with_suffix(".md")
    out_md.write_text(md_content, encoding="utf-8")
    print(f"提取完成！已儲存至 {out_md}")
