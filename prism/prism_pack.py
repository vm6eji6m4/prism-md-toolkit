import os
import sys
import re
import json
import hashlib
from pathlib import Path
from datetime import datetime

# GUI 為選配（外審 TOP2）：headless/CI 環境沒有 Tk 也要能跑 CLI，故懶載入
try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    from tkinter.scrolledtext import ScrolledText
    _TK_AVAILABLE = True
except Exception:  # noqa: BLE001
    _TK_AVAILABLE = False


def is_within(child, ancestor) -> bool:
    """嚴格層級判定（外審 TOP1）：realpath+normcase+commonpath，防 symlink/UNC/大小寫繞過。"""
    c = os.path.normcase(os.path.realpath(str(child)))
    a = os.path.normcase(os.path.realpath(str(ancestor)))
    try:
        return os.path.commonpath([c, a]) == a
    except ValueError:
        return False

# Configurations
CACHE_VERSION = "v3.4"
# 公開版：不預設任何個人路徑；CLI 必須明給來源，輸出預設寫到「當前工作目錄」
DEFAULT_SRC = ""
DEFAULT_OUT_DIR = "."
DEFAULT_OUT_FILE = "packaged_skills.md"
DEFAULT_CHUNK_LIMIT = 500000  # Default token split limit
MAX_FILE_SIZE_KB = 500  # Skip files larger than 500KB to save tokens

# Core settings
EXCLUDE_DIRS = {
    ".git", ".obsidian", ".quarantine", ".archive", 
    "__pycache__", "node_modules", "venv", ".venv",
    ".github", ".vscode", ".pytest_cache", ".idea",
    "build", "dist", "site-packages", "lib", "libs"
}

EXCLUDE_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", 
    ".zip", ".tar", ".gz", ".rar", ".7z", ".exe", 
    ".dll", ".so", ".pyc", ".db", ".sqlite", ".mp3", 
    ".mp4", ".avi", ".mkv", ".wav", ".flac"
}

EXCLUDE_FILES = {
    "package-lock.json", "poetry.lock", "pnpm-lock.yaml", 
    "cargo.lock", "yarn.lock", "composer.lock"
}

# Helpers
def calculate_sha256(file_path: Path) -> str:
    sha256 = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256.update(byte_block)
        return sha256.hexdigest()
    except Exception:
        return ""

def is_text_file(file_path: Path, max_size_kb: int) -> bool:
    try:
        if file_path.name.lower() in EXCLUDE_FILES:
            return False
        if file_path.stat().st_size > max_size_kb * 1024:
            return False
        with open(file_path, "rb") as f:
            chunk = f.read(1024)
            return b"\x00" not in chunk
    except Exception:
        return False

def clean_content(text: str) -> str:
    lines = [line.rstrip() for line in text.splitlines()]
    cleaned_lines = []
    prev_blank = False
    for line in lines:
        if not line:
            if not prev_blank:
                cleaned_lines.append(line)
                prev_blank = True
        else:
            cleaned_lines.append(line)
            prev_blank = False
    return "\n".join(cleaned_lines).strip()

def generate_auto_summary(file_path: Path, content: str) -> str:
    suffix = file_path.suffix.lower()
    summary_lines = []
    
    if suffix == ".py":
        imports = re.findall(r"^(?:import\s+[\w, ]+|from\s+[\w\.]+\s+import\s+[\w, \* ]+)", content, re.MULTILINE)
        classes = re.findall(r"^class\s+(\w+)", content, re.MULTILINE)
        functions = re.findall(r"^def\s+(\w+)", content, re.MULTILINE)
        summary_lines.append("Helps AI: Run python script")
        if imports:
            summary_lines.append(f"Imports: {', '.join(imports[:3])}" + ("..." if len(imports) > 3 else ""))
        if classes:
            summary_lines.append(f"Classes: {', '.join(classes[:5])}" + ("..." if len(classes) > 5 else ""))
        if functions:
            summary_lines.append(f"Functions: {', '.join(functions[:8])}" + ("..." if len(functions) > 8 else ""))
    elif suffix in (".md", ".mdx"):
        headers = re.findall(r"^(#{1,3})\s+(.+)$", content, re.MULTILINE)
        summary_lines.append("Helps AI: Read documentation")
        if headers:
            summary_lines.append("Key Sections: " + ", ".join(title.strip() for level, title in headers[:5]) + ("..." if len(headers) > 5 else ""))
    elif suffix in (".json", ".yaml", ".yml", ".toml"):
        summary_lines.append("Helps AI: Read config structure")
        try:
            if suffix == ".json":
                data = json.loads(content)
                if isinstance(data, dict):
                    keys = list(data.keys())
                    summary_lines.append(f"Keys: {', '.join(keys[:10])}")
            elif suffix in (".yaml", ".yml"):
                keys = re.findall(r"^([\w\-]+)\s*:", content, re.MULTILINE)
                if keys:
                    summary_lines.append(f"Keys: {', '.join(keys[:10])}")
        except Exception:
            pass
    if not summary_lines or len(summary_lines) == 1:
        lines = content.splitlines()
        non_empty = [l.strip() for l in lines if l.strip()][:2]
        if non_empty:
            summary_lines.append(f"Preview: {'; '.join(non_empty)}")
    return "; ".join(summary_lines)

def estimate_tokens(text: str) -> int:
    try:
        import tiktoken
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text, disallowed_special=()))
    except Exception:
        char_count = len(text)
        word_count = len(text.split())
        return int(char_count * 0.6 + word_count * 0.8)

def get_file_priority(file_path: Path, sources: list[Path] = None) -> tuple[int, str]:
    name_upper = file_path.name.upper()
    path_str = file_path.as_posix().lower()
    suffix = file_path.suffix.lower()
    
    # Level 7: Test/Example (lowest priority)
    if "test" in name_upper or "/tests/" in path_str or "/test_" in path_str or "example" in path_str or "examples" in path_str:
        return (7, "★☆☆☆☆ (Test/Example)")
        
    # Level 0: Global Index (specifically manifest or packaged index files generated by this tool)
    is_global_index = (
        name_upper in ("PACKAGED_SKILLS.MD", "PACKAGED_OUTPUT.MD") or
        (name_upper.endswith("MANIFEST.JSON") and any(k in name_upper for k in ("PACKAGED_SKILLS", "PACKAGED_OUTPUT"))) or
        (name_upper.startswith("PACKAGED_SKILLS_PART") or name_upper.startswith("PACKAGED_OUTPUT_PART"))
    )
    if is_global_index:
        return (0, "★★★★★ (Global Index)")
        
    # Level 1 or 3: Architecture/Key Docs (README, SKILL, CLAUDE, etc.)
    if any(k in name_upper for k in ("README", "SKILL", "CLAUDE", "AGENTS", "_BRIEFING", "ARCHITECTURE", "DESIGN", "PROPOSAL")):
        is_root_doc = False
        if sources:
            for src in sources:
                try:
                    if file_path.is_relative_to(src):
                        rel_path = file_path.relative_to(src)
                        # Root document or top-level sub-folder root document (depth <= 2 parts)
                        if len(rel_path.parts) <= 2:
                            is_root_doc = True
                            break
                except Exception:
                    pass
        else:
            is_root_doc = True
            
        if is_root_doc:
            return (1, "★★★★★ (Core Architecture)")
        else:
            return (3, "★★★★☆ (Sub-module Doc)")
        
    # Level 2: Main Entry Scripts
    if suffix == ".py" and any(k in name_upper for k in ("CLI", "MAIN", "PACK_TO_MD")):
        return (2, "★★★★★ (Main Entry Point)")
        
    # Level 4: Configuration
    if suffix in (".json", ".yaml", ".yml", ".env", ".ini", ".cfg", ".toml", ".lock"):
        return (4, "★★★★☆ (Config & Settings)")
        
    # Level 5: Core Code
    if suffix in (".py", ".js", ".ts", ".tsx", ".jsx", ".cpp", ".h", ".go", ".rs", ".java", ".cs", ".sql"):
        return (5, "★★★☆☆ (Core Code)")
        
    # Level 6: Utility / General
    return (6, "★★☆☆☆ (Utility)")

def get_dir_tree(sources: list[Path], files_list: list[Path]) -> str:
    tree = []
    files_set = {f.resolve() for f in files_list}
    ancestor_dirs = set()
    for f in files_list:
        ancestor_dirs.update(f.resolve().parents)
        
    def _build_tree(dir_path: Path, prefix=""):
        try:
            entries = sorted(list(dir_path.iterdir()), key=lambda e: (not e.is_dir(), e.name.lower()))
        except PermissionError:
            return
        filtered_entries = []
        for entry in entries:
            resolved_entry = entry.resolve()
            if entry.is_dir():
                if entry.name.startswith(".") or entry.name.lower() in EXCLUDE_DIRS:
                    continue
                if resolved_entry in ancestor_dirs:
                    filtered_entries.append(entry)
            else:
                if resolved_entry in files_set:
                    filtered_entries.append(entry)
        for i, entry in enumerate(filtered_entries):
            is_last = (i == len(filtered_entries) - 1)
            connector = "└── " if is_last else "├── "
            tree.append(f"{prefix}{connector}{entry.name}")
            if entry.is_dir():
                next_prefix = prefix + ("    " if is_last else "│   ")
                _build_tree(entry, next_prefix)

    for src in sorted(sources, key=lambda p: p.name.lower()):
        if src.is_dir():
            tree.append(src.name)
            _build_tree(src)
        else:
            if src.resolve() in files_set:
                tree.append(src.name)
    return "\n".join(tree)

# Decoupled Core Packaging Logic
def run_pack_logic(sources: list[Path], out_file_path: Path, chunk_limit: int, max_size_kb: int, lite_mode: bool, summary_only: bool, log_callback=None, progress_callback=None):
    def log(msg):
        if log_callback:
            log_callback(msg)
        else:
            print(msg)
            
    def set_progress(val, max_val=None):
        if progress_callback:
            progress_callback(val, max_val)

    log("================ 正在初始化打包程式 ================")
    log(f"目標儲存路徑: {out_file_path}")
    log(f"分包限制: {chunk_limit}")
    if summary_only:
        log("模式：僅打包摘要 (不含內文)")
    # Load incremental metadata cache
    cache_data = {}
    manifest_path = out_file_path.parent / f"{out_file_path.stem}_manifest.json"
    if manifest_path.exists():
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                old_manifest = json.load(f)
                if old_manifest.get("cache_version") == CACHE_VERSION:
                    for part in old_manifest.get("parts", []):
                        for f_entry in part.get("file_metadata", []):
                            cache_data[f_entry["path"]] = f_entry
                    log(f"已成功載入增量快取清單：{manifest_path.name}")
                else:
                    log(f"快取版本不相符 (目前: {CACHE_VERSION}, 快取: {old_manifest.get('cache_version')})，將重新分析與生成摘要。")
        except Exception as e:
            log(f"載入快取失敗 (將進行全新掃描): {e}")
            
    # Scan and collect all valid files
    files_to_pack = []
    exclude_dirs_lower = {x.lower() for x in EXCLUDE_DIRS}
    
    for src in sources:
        if src.is_file():
            if is_text_file(src, max_size_kb):
                files_to_pack.append(src)
            else:
                log(f"跳過檔案: {src.name} (不符文字類型或大小過濾)")
        elif src.is_dir():
            log(f"正在掃描資料夾: {src.name}...")
            for root, dirs, files in os.walk(src):
                dirs[:] = [d for d in dirs if d.lower() not in exclude_dirs_lower and not d.startswith(".")]
                for file in files:
                    file_path = Path(root) / file
                    if file_path.suffix.lower() in EXCLUDE_EXTS:
                        continue
                    if lite_mode:
                        name_upper = file_path.name.upper()
                        is_lite = ("SKILL.MD" in name_upper or 
                                   "README.MD" in name_upper or 
                                   "_BRIEFING.MD" in name_upper or 
                                   "CLAUDE.MD" in name_upper)
                        if not is_lite:
                            continue
                    if is_text_file(file_path, max_size_kb):
                        files_to_pack.append(file_path)
                        
    # De-duplicate files
    files_to_pack = list(set(files_to_pack))
    # Sort: highest priority first (Level 0), alphabetical name second
    files_to_pack.sort(key=lambda f: (get_file_priority(f, sources)[0], f.as_posix().lower()))
    
    log(f"掃描完畢，共找到 {len(files_to_pack)} 個相容的檔案。")
    if not files_to_pack:
        log("無符合條件的檔案，終止程序。")
        set_progress(100, 100)
        return
        
    log("正在生成目錄結構樹...")
    dir_tree = get_dir_tree(sources, files_to_pack)
    
    set_progress(0, len(files_to_pack))
    
    # Analyze metadata step (O(1) memory)
    log("正在分析檔案雜湊與 Token 數 (啟用增量比對)...")
    file_metadata_list = []
    cache_hits = 0
    
    for idx, file_path in enumerate(files_to_pack, 1):
        set_progress(idx, len(files_to_pack))
        
        # Find the best relative path reference
        rel_path = file_path.name
        for src in sources:
            if src.is_dir() and file_path.is_relative_to(src):
                rel_path = f"{src.name}/{file_path.relative_to(src).as_posix()}"
                break
                
        file_hash = calculate_sha256(file_path)
        priority_val, priority_stars = get_file_priority(file_path, sources)
        
        cached = cache_data.get(rel_path)
        if cached and cached.get("sha256") == file_hash:
            file_metadata_list.append({
                "path": rel_path,
                "local_path": file_path,
                "sha256": file_hash,
                "lines": cached["lines"],
                "size": cached["size"],
                "tokens": cached["tokens"],
                "suffix": cached["suffix"],
                "type": cached["type"],
                "priority_val": priority_val,
                "priority": priority_stars,
                "summary": cached.get("summary", "")
            })
            cache_hits += 1
        else:
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except Exception:
                continue
            cleaned = clean_content(content)
            auto_summary = generate_auto_summary(file_path, cleaned)
            lines_count = len(cleaned.splitlines())
            size_bytes = len(cleaned.encode("utf-8", errors="ignore"))
            file_tokens = estimate_tokens(cleaned)
            
            file_metadata_list.append({
                "path": rel_path,
                "local_path": file_path,
                "sha256": file_hash,
                "lines": lines_count,
                "size": size_bytes,
                "tokens": file_tokens,
                "suffix": file_path.suffix.lstrip("."),
                "type": "documentation" if "md" in file_path.suffix.lower() else "code",
                "priority_val": priority_val,
                "priority": priority_stars,
                "summary": auto_summary
            })
            
    log(f"雜湊比對完成！快取命中：{cache_hits} 個檔案，重新處理：{len(files_to_pack) - cache_hits} 個檔案。")
    
    # Assign sequential 3-digit ID to each file metadata entry
    for idx, f in enumerate(file_metadata_list, 1):
        f["id"] = f"{idx:03d}"
        
    # Calculate advanced statistics
    lang_counts = {}
    for f in file_metadata_list:
        ext = f["suffix"] if f["suffix"] else "unknown"
        lang_counts[ext] = lang_counts.get(ext, 0) + 1
    lang_stats_str = ", ".join(f"{ext}: {count}" for ext, count in sorted(lang_counts.items(), key=lambda x: -x[1]))
    
    cat_counts = {}
    for f in file_metadata_list:
        cat = f["priority"]
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
    cat_stats_str = ", ".join(f"{cat}: {count}" for cat, count in sorted(cat_counts.items(), key=lambda x: x[0]))
    
    # Get Top 5 Core files
    top_5_files = sorted(file_metadata_list, key=lambda x: (x["priority_val"], x["path"]))[:5]
    
    # Partition files
    chunks = []
    current_chunk = []
    current_chunk_tokens = 0
    
    for f in file_metadata_list:
        effective_tokens = f["tokens"] if not summary_only else 50
        if current_chunk_tokens + effective_tokens > chunk_limit and current_chunk:
            chunks.append(current_chunk)
            current_chunk = []
            current_chunk_tokens = 0
        current_chunk.append(f)
        current_chunk_tokens += effective_tokens
        
    if current_chunk:
        chunks.append(current_chunk)
        
    # Write output files sequentially (O(1) memory content streaming)
    log("開始串流打包寫入 LKP 結構 (v3.4)...")
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    manifest_parts = []
    
    out_dir = out_file_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    
    for part_idx, chunk_files in enumerate(chunks, 1):
        part_suffix = f"_part{part_idx}" if len(chunks) > 1 else ""
        out_file_name = f"{out_file_path.stem}{part_suffix}{out_file_path.suffix}"
        out_path = out_dir / out_file_name
        
        chunk_lines = sum(f["lines"] for f in chunk_files)
        chunk_size = sum(f["size"] for f in chunk_files)
        
        log(f"正在串流寫入分包: {out_file_name}...")
        
        # Helper function to generate the index text dynamically
        def make_index_text(estimated_tokens_str):
            lines = []
            lines.append("# LLM Knowledge Package (LKP v3.4)")
            lines.append(f"- **包序列 (Part)**: {part_idx} of {len(chunks)}")
            lines.append(f"- **生成時間 (Timestamp)**: `{timestamp_str}`")
            lines.append(f"- **來源個數 (Scope)**: {len(sources)} sources")
            if summary_only:
                lines.append("- **打包模式 (Type)**: `Summary-Only Lite Index (僅大綱索引，無內文區)`\n")
            else:
                lines.append("")
                
            lines.append("> [!IMPORTANT]")
            lines.append("> **AI Instruction & Reading Strategy (AI 閱讀策略)**:")
            lines.append("> 1. **Core First**: Read the Top Core Files listed in Section 1 first to grasp architectural core.")
            lines.append("> 2. **Statistics & Skeleton**: Scan Section 2 (Statistics) and Section 3 (Directory Structure tree).")
            lines.append("> 3. **Search Index**: Use Section 4 (High-Density File Index) to query files, priority star ratings, and summaries.")
            lines.append("> 4. **Locate Target Files**: Find specific files using the 3-digit padded ID references.")
            lines.append("> 5. **Read File Tag Content**: Only when necessary, look up corresponding `<file path=\"...\">` tags and read raw contents.\n")
            
            lines.append("## 1. Top Core Files (最核心關鍵檔案)")
            for idx_t, ft in enumerate(top_5_files, 1):
                lines.append(f"{idx_t}. **[{ft['id']}] {ft['path']}** `{ft['priority']}`: {ft['summary'] if ft['summary'] else '重要架構大綱與說明文件'}")
            lines.append("")
            
            lines.append("## 2. Package Statistics (全局數據統計)")
            lines.append(f"- **本包檔案數**: {len(chunk_files)}")
            lines.append(f"- **本包總行數**: {chunk_lines}")
            lines.append(f"- **預估總 Token 數**: {estimated_tokens_str}")
            lines.append(f"- **語言分佈 (Languages)**: {lang_stats_str}")
            lines.append(f"- **級別分佈 (Categories)**: {cat_stats_str}\n")
            
            lines.append("## 3. Directory Structure (目錄結構)")
            lines.append("> **Legend**: 📄 Document/MD | ⚙ Config | 🐍 Python | 📦 Package | 🧪 Test\n")
            lines.append("```text")
            lines.append(dir_tree)
            lines.append("```\n")
            
            lines.append("## 4. High-Density File Index (高密度檔案索引表)")
            lines.append("| ID | File Path | Lang | Lines | Est. Tokens | Priority | Auto-Summary |")
            lines.append("|---|---|---|---|---|---|---|")
            for f_item in chunk_files:
                lines.append(f"| {f_item['id']} | {f_item['path']} | {f_item['suffix']} | {f_item['lines']} | {f_item['tokens']:,} | {f_item['priority']} | {f_item['summary']} |")
            lines.append("")
            
            return "\n".join(lines)

        # Estimate and generate the index text
        if summary_only:
            dummy_index = make_index_text("~9,999,999 tokens")
            estimated_tokens = estimate_tokens(dummy_index)
            final_index_text = make_index_text(f"~{estimated_tokens:,} tokens (Lite index)")
            chunk_tokens = estimated_tokens
        else:
            raw_files_tokens = sum(f["tokens"] for f in chunk_files)
            # Estimate header + index overhead
            dummy_index = make_index_text("~9,999,999 tokens")
            index_overhead = estimate_tokens(dummy_index)
            total_est_tokens = raw_files_tokens + index_overhead
            final_index_text = make_index_text(f"~{total_est_tokens:,} tokens")
            chunk_tokens = total_est_tokens

        with open(out_path, "w", encoding="utf-8") as out_f:
            out_f.write(final_index_text)
            
            # Write files contents only if NOT in summary_only mode (completely strip redundancy in summary mode)
            if not summary_only:
                out_f.write("\n" + "=" * 80 + "\n\n")
                out_f.write("## 5. Files Content (檔案詳細內容區)\n\n")
                
                # Write each file's content one-by-one (O(1) memory complexity)
                for f in chunk_files:
                    out_f.write(f"### 📄 [{f['id']}] 檔案：`{f['path']}` (Priority: {f['priority']})\n\n")
                    out_f.write(f'<file path="{f["path"]}" language="{f["suffix"]}" lines="{f["lines"]}" size_bytes="{f["size"]}" type="{f["type"]}" tokens="{f["tokens"]}" priority="{f["priority"]}">\n')
                    
                    try:
                        with open(f["local_path"], "r", encoding="utf-8", errors="ignore") as in_f:
                            file_content = in_f.read()
                    except Exception:
                        file_content = "[讀取失敗]"
                    cleaned_file_content = clean_content(file_content)
                    
                    suffix = f["suffix"].strip()
                    if suffix in ("md", "mdx"):
                        out_f.write(f"````{suffix}\n")
                        out_f.write(cleaned_file_content + "\n")
                        out_f.write("````\n")
                    else:
                        out_f.write(f"```{suffix if suffix else 'text'}\n")
                        out_f.write(cleaned_file_content + "\n")
                        out_f.write("```\n")
                        
                    out_f.write("</file>\n\n")
                    out_f.write("---\n\n")
                    
        # Add to manifest
        manifest_parts.append({
            "part": part_idx,
            "filename": out_file_name,
            "token_count": chunk_tokens,
            "file_count": len(chunk_files),
            "file_metadata": [
                {
                    "path": f["path"],
                    "sha256": f["sha256"],
                    "lines": f["lines"],
                    "size": f["size"],
                    "tokens": f["tokens"],
                    "suffix": f["suffix"],
                    "type": f["type"],
                    "priority": f["priority"],
                    "summary": f["summary"]
                } for f in chunk_files
            ]
        })
        log(f"  └ 成功寫入 {out_file_name}")
        
    manifest_path = out_dir / f"{out_file_path.stem}_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as mf:
        json.dump({
            "timestamp": timestamp_str,
            "cache_version": CACHE_VERSION,
            "total_parts": len(chunks),
            "total_files": len(file_metadata_list),
            "parts": manifest_parts
        }, mf, indent=2)
    log(f"成功寫入增量更新主索引：{manifest_path.name}")
    log("================ 打包作業已成功完成！ ================")
    return len(chunks)

# GUI Application Class
class PackagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI 知識打包封裝器 v3.4 (GUI版)")
        self.root.geometry("850x680")
        self.root.minsize(700, 500)
        
        self.sources = []
        self.style = ttk.Style()
        self.style.theme_use("vista" if sys.platform == "win32" else "default")
        
        self.create_widgets()
        
    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        title_label = ttk.Label(main_frame, text="AI 知識打包封裝器 (LLM Optimized)", font=("Microsoft JhengHei", 16, "bold"))
        title_label.pack(pady=(0, 10), anchor=tk.W)
        
        src_frame = ttk.LabelFrame(main_frame, text=" 選擇要打包的來源資料 (資料夾或檔案) ", padding="10")
        src_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        list_container = ttk.Frame(src_frame)
        list_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.src_listbox = tk.Listbox(list_container, font=("Segoe UI", 9), selectmode=tk.SINGLE)
        self.src_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_container, orient=tk.VERTICAL, command=self.src_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.src_listbox.config(yscrollcommand=scrollbar.set)
        
        btn_frame = ttk.Frame(src_frame, padding="5")
        btn_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        
        ttk.Button(btn_frame, text="新增資料夾...", command=self.add_directory).pack(fill=tk.X, pady=3)
        ttk.Button(btn_frame, text="新增檔案...", command=self.add_files).pack(fill=tk.X, pady=3)
        ttk.Button(btn_frame, text="刪除選取", command=self.remove_selected).pack(fill=tk.X, pady=3)
        ttk.Button(btn_frame, text="清空全部", command=self.clear_all).pack(fill=tk.X, pady=3)
        
        dest_frame = ttk.LabelFrame(main_frame, text=" 儲存與模式設定 ", padding="10")
        dest_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(dest_frame, text="輸出 MD 檔案路徑:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.dest_entry = ttk.Entry(dest_frame, width=60)
        self.dest_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        
        default_dest = os.path.join(os.getcwd(), "packaged_output.md")
        self.dest_entry.insert(0, default_dest)
        
        ttk.Button(dest_frame, text="瀏覽...", command=self.browse_dest).grid(row=0, column=2, padx=5, pady=5)
        
        param_frame = ttk.Frame(dest_frame)
        param_frame.grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=(5, 0))
        
        self.chunk_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(param_frame, text="自動分包上限 (Tokens):", variable=self.chunk_var, command=self.toggle_chunk).grid(row=0, column=0, sticky=tk.W)
        
        self.chunk_entry = ttk.Entry(param_frame, width=12)
        self.chunk_entry.insert(0, "500000")
        self.chunk_entry.grid(row=0, column=1, padx=5)
        
        ttk.Label(param_frame, text="單檔限制 (KB):").grid(row=0, column=2, padx=(15, 5), sticky=tk.W)
        self.size_entry = ttk.Entry(param_frame, width=8)
        self.size_entry.insert(0, "500")
        self.size_entry.grid(row=0, column=3, padx=5)
        
        self.lite_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(param_frame, text="極簡模式 (僅打包大綱/說明文件)", variable=self.lite_var).grid(row=0, column=4, padx=(10, 5), sticky=tk.W)
        
        self.summary_only_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(param_frame, text="僅打包摘要 (不含檔案內文)", variable=self.summary_only_var).grid(row=0, column=5, padx=(10, 5), sticky=tk.W)
        
        dest_frame.columnconfigure(1, weight=1)
        
        console_frame = ttk.LabelFrame(main_frame, text=" 執行進度與日誌 ", padding="10")
        console_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.log_text = ScrolledText(console_frame, height=8, font=("Consolas", 9), state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        self.progress = ttk.Progressbar(main_frame, orient=tk.HORIZONTAL, mode='determinate')
        self.progress.pack(fill=tk.X, pady=(5, 5))
        
        self.pack_button = ttk.Button(main_frame, text="🚀 開始打包 AI 知識包", command=self.start_packaging)
        self.pack_button.pack(fill=tk.X, pady=(5, 0))
        
    def toggle_chunk(self):
        if self.chunk_var.get():
            self.chunk_entry.config(state=tk.NORMAL)
        else:
            self.chunk_entry.config(state=tk.DISABLED)
            
    def log(self, message):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update_idletasks()
        
    def set_progress_val(self, val, max_val=None):
        if max_val is not None:
            self.progress['maximum'] = max_val
        self.progress['value'] = val
        self.root.update_idletasks()
        
    def add_directory(self):
        dir_path = filedialog.askdirectory(title="選擇要加入的資料夾")
        if dir_path:
            p = Path(dir_path).resolve()
            if p not in self.sources:
                self.sources.append(p)
                self.src_listbox.insert(tk.END, f"[資料夾] {p}")
                
    def add_files(self):
        file_paths = filedialog.askopenfilenames(title="選擇要加入的檔案", filetypes=[("文字檔與程式碼", "*.txt;*.md;*.py;*.js;*.ts;*.json;*.yaml;*.yml;*.sh;*.bat;*.ps1;*.ini;*.cfg;*.sql;*.html;*.css"), ("所有檔案", "*.*")])
        if file_paths:
            for f in file_paths:
                p = Path(f).resolve()
                if p not in self.sources:
                    self.sources.append(p)
                    self.src_listbox.insert(tk.END, f"[檔案] {p}")
                    
    def remove_selected(self):
        selection = self.src_listbox.curselection()
        if selection:
            idx = selection[0]
            self.src_listbox.delete(idx)
            del self.sources[idx]
            
    def clear_all(self):
        self.src_listbox.delete(0, tk.END)
        self.sources.clear()
        
    def browse_dest(self):
        file_path = filedialog.asksaveasfilename(title="選擇儲存目標 Markdown 檔案", defaultextension=".md", filetypes=[("Markdown 檔案", "*.md")])
        if file_path:
            self.dest_entry.delete(0, tk.END)
            self.dest_entry.insert(0, file_path)
            
    def start_packaging(self):
        if not self.sources:
            messagebox.showwarning("警告", "請至少加入一個來源資料夾或檔案！")
            return
            
        out_file_path = self.dest_entry.get().strip()
        if not out_file_path:
            messagebox.showwarning("警告", "請指定輸出 Markdown 檔案路徑！")
            return
            
        try:
            max_size_kb = int(self.size_entry.get())
        except ValueError:
            messagebox.showerror("錯誤", "單檔大小限制必須是數字！")
            return
            
        chunk_limit = 9999999999
        if self.chunk_var.get():
            try:
                chunk_limit = int(self.chunk_entry.get())
            except ValueError:
                messagebox.showerror("錯誤", "分包上限必須是數字！")
                return
                
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        
        self.pack_button.config(state=tk.DISABLED)
        self.progress['value'] = 0
        
        try:
            parts_written = run_pack_logic(
                sources=self.sources,
                out_file_path=Path(out_file_path),
                chunk_limit=chunk_limit,
                max_size_kb=max_size_kb,
                lite_mode=self.lite_var.get(),
                summary_only=self.summary_only_var.get(),
                log_callback=self.log,
                progress_callback=self.set_progress_val
            )
            if parts_written:
                try:
                    os.startfile(Path(out_file_path).parent)
                except Exception:
                    pass
                messagebox.showinfo("成功", f"打包完成！\n共寫入 {parts_written} 個分包檔案。\n已自動開啟輸出資料夾。")
        except Exception as e:
            self.log(f"發生未預期的錯誤: {e}")
            messagebox.showerror("打包失敗", f"打包過程中出錯：\n{e}")
        finally:
            self.pack_button.config(state=tk.NORMAL)

# Headless CLI Runner
def run_cli_mode(src_input, lite_mode, summary_only, out_dir_arg=None):
    print("=" * 60)
    print("      AI 優化型 Markdown 打包工具 v3.4 (命令列版)      ")
    print("=" * 60)
    
    if not src_input:
        print("用法: python prism_pack.py <SOURCE_DIR> [-s|--summary] [-l|--lite] [-o 輸出目錄]")
        sys.exit(1)
    src_path = Path(src_input).resolve()

    if not src_path.exists():
        print(f"錯誤：來源路徑 '{src_path}' 不存在。")
        sys.exit(1)
        
    out_dir = Path(out_dir_arg or DEFAULT_OUT_DIR).resolve()
    # 安全閘：輸出不准落在來源樹內（realpath 層級判定，全工具箱鐵律）
    if is_within(out_dir, src_path):
        print(f"拒絕：輸出目錄 {out_dir} 位於來源樹內，請用 -o 指定樹外路徑")
        sys.exit(1)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file_path = out_dir / DEFAULT_OUT_FILE
    
    # CLI packaging
    run_pack_logic(
        sources=[src_path],
        out_file_path=out_file_path,
        chunk_limit=DEFAULT_CHUNK_LIMIT,
        max_size_kb=MAX_FILE_SIZE_KB,
        lite_mode=lite_mode,
        summary_only=summary_only,
        log_callback=None,
        progress_callback=None
    )

USAGE = ("用法: python prism_pack.py <SOURCE_DIR> [-s|--summary] [-l|--lite] [-o 輸出目錄]\n"
         "      python prism_pack.py --gui   # 明確啟動 Tkinter 介面（headless 環境勿用）")


def main():
    interactive = False
    lite_mode = False
    summary_only = False
    src_input = ""

    args = sys.argv[1:]
    # 外審 TOP2：GUI 必須顯式要求；無參數一律印 usage，CI/headless 不會卡死
    if "--gui" in args or "-i" in args or "--interactive" in args:
        interactive = True
        args = [a for a in args if a not in ("--gui", "-i", "--interactive")]
        
    if "-l" in args or "--lite" in args:
        lite_mode = True
        args = [a for a in args if a not in ("-l", "--lite")]
        
    if "-s" in args or "--summary" in args:
        summary_only = True
        args = [a for a in args if a not in ("-s", "--summary")]

    out_dir_arg = None
    for flag in ("-o", "--out"):
        if flag in args:
            i = args.index(flag)
            if i + 1 >= len(args):
                print(f"錯誤：{flag} 需要一個輸出目錄參數")
                sys.exit(1)
            out_dir_arg = args[i + 1]
            args = args[:i] + args[i + 2:]

    if args:
        src_input = args[0]

    if src_input and not interactive:
        # CLI Mode
        run_cli_mode(src_input, lite_mode, summary_only, out_dir_arg)
    elif interactive:
        # GUI Mode（僅 --gui 顯式要求時）
        if not _TK_AVAILABLE:
            print("錯誤：此環境沒有 Tkinter，無法啟動 GUI。請改用 CLI 模式。")
            print(USAGE)
            sys.exit(1)
        root = tk.Tk()
        app = PackagerApp(root)
        root.mainloop()
    else:
        print(USAGE)
        sys.exit(1)

if __name__ == "__main__":
    main()
