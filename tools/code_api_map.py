# -*- coding: utf-8 -*-
"""
code_api_map.py — 對任意 Python 專案產生 CODE_API_MAP.md（LLM 導航用 API 骨架地圖）
改良自 Antigravity code_mind_compiler.py（2026-07-16 Claude 參數化＋去 networkx 硬依賴）。

與 codegraph MCP 的分工：
  codegraph = 對話中即時深度分析（impact/dataflow/semantic search，需 MCP 環境）
  本工具   = 建置期產「可攜帶的 md 快照」→ 塞進委外 BRIEF 包 / PRISM 知識包（無 MCP 環境也能讀）

用法：
  py -3.11 code_api_map.py <專案目錄> [-o CODE_API_MAP.md] [--db code_structure.db]
輸出永遠寫到 -o 指定路徑（預設當前目錄），絕不寫入來源樹。
"""
import argparse
import ast
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

SKIP_DIRS = {".venv", "venv", "node_modules", "__pycache__", ".git",
             "dist", "build", ".archive", ".quarantine", "runtime"}


def iter_py_files(root: Path):
    for p in sorted(root.rglob("*.py")):
        parts = p.relative_to(root).parts
        # 隱藏目錄（.venv-merge/.claude/.git…）與已知雜訊目錄一律跳過
        if any(part.lower() in SKIP_DIRS or part.startswith(".") for part in parts[:-1]):
            continue
        yield p


def unparse(node) -> str:
    try:
        return ast.unparse(node) if node is not None else "None"
    except Exception:  # noqa: BLE001
        return "?"


def compile_project(root: Path, db_path: Path) -> dict:
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.executescript("""
    DROP TABLE IF EXISTS modules; DROP TABLE IF EXISTS classes;
    DROP TABLE IF EXISTS functions; DROP TABLE IF EXISTS imports;
    CREATE TABLE modules(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, path TEXT, docstring TEXT, mtime TEXT);
    CREATE TABLE classes(id INTEGER PRIMARY KEY AUTOINCREMENT, module_id INT, name TEXT, bases TEXT, docstring TEXT);
    CREATE TABLE functions(id INTEGER PRIMARY KEY AUTOINCREMENT, module_id INT, class_id INT,
                           name TEXT, args TEXT, returns TEXT, docstring TEXT);
    CREATE TABLE imports(id INTEGER PRIMARY KEY AUTOINCREMENT, module_id INT, name TEXT);
    """)
    stats = {"modules": 0, "classes": 0, "functions": 0, "skipped": 0}
    for py in iter_py_files(root):
        try:
            tree = ast.parse(py.read_text(encoding="utf-8", errors="ignore"))
        except SyntaxError:
            stats["skipped"] += 1
            continue
        rel = py.relative_to(root).as_posix()
        cur.execute("INSERT INTO modules(name,path,docstring,mtime) VALUES(?,?,?,?)",
                    (rel, str(py), ast.get_docstring(tree) or "",
                     datetime.fromtimestamp(py.stat().st_mtime).strftime("%Y-%m-%d %H:%M")))
        mid = cur.lastrowid
        stats["modules"] += 1
        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [a.name for a in node.names]
                base = getattr(node, "module", None)
                for n in names:
                    cur.execute("INSERT INTO imports(module_id,name) VALUES(?,?)",
                                (mid, f"{base}.{n}" if base else n))
            elif isinstance(node, ast.ClassDef):
                cur.execute("INSERT INTO classes(module_id,name,bases,docstring) VALUES(?,?,?,?)",
                            (mid, node.name, ",".join(unparse(b) for b in node.bases),
                             ast.get_docstring(node) or ""))
                cid = cur.lastrowid
                stats["classes"] += 1
                for m in node.body:
                    if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        cur.execute(
                            "INSERT INTO functions(module_id,class_id,name,args,returns,docstring) VALUES(?,?,?,?,?,?)",
                            (mid, cid, m.name, unparse_args(m), unparse(m.returns),
                             ast.get_docstring(m) or ""))
                        stats["functions"] += 1
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                cur.execute(
                    "INSERT INTO functions(module_id,class_id,name,args,returns,docstring) VALUES(?,NULL,?,?,?,?)",
                    (mid, node.name, unparse_args(node), unparse(node.returns),
                     ast.get_docstring(node) or ""))
                stats["functions"] += 1
    con.commit()
    con.close()
    return stats


def unparse_args(fn) -> str:
    try:
        return ast.unparse(fn.args)
    except Exception:  # noqa: BLE001
        return "..."


def generate_map(db_path: Path, out_path: Path, root: Path):
    con = sqlite3.connect(db_path)
    # 外層迭代與內層查詢必須用不同 cursor，否則外層迭代會被內層 execute 打斷（只剩第一列）
    cur, cur2, cur3 = con.cursor(), con.cursor(), con.cursor()
    md = [f"# 🧠 CODE API MAP — {root}",
          f"> 產生於 {datetime.now():%Y-%m-%d %H:%M}；供 LLM 導航，讀此檔即可掌握全案 API，勿逐檔生吞原始碼。", ""]
    for mid, name, doc in cur.execute("SELECT id,name,docstring FROM modules ORDER BY name"):
        md.append(f"## 📦 `{name}`")
        if doc:
            md.append(f"> {doc.splitlines()[0]}")
        imps = [r[0] for r in cur2.execute("SELECT name FROM imports WHERE module_id=?", (mid,))]
        if imps:
            md.append(f"- imports: `{', '.join(sorted(set(imps))[:15])}`")
        for cid, cname, bases, cdoc in cur2.execute("SELECT id,name,bases,docstring FROM classes WHERE module_id=?", (mid,)):
            md.append(f"### 🏛 class `{cname}({bases})` — {(cdoc or '').splitlines()[0] if cdoc else ''}")
            for fname, fargs, fret, fdoc in cur3.execute("SELECT name,args,returns,docstring FROM functions WHERE class_id=?", (cid,)):
                d = f" — {fdoc.splitlines()[0]}" if fdoc else ""
                md.append(f"- `def {fname}({fargs}) -> {fret}`{d}")
        for fname, fargs, fret, fdoc in cur2.execute("SELECT name,args,returns,docstring FROM functions WHERE module_id=? AND class_id IS NULL", (mid,)):
            d = f" — {fdoc.splitlines()[0]}" if fdoc else ""
            md.append(f"- `def {fname}({fargs}) -> {fret}`{d}")
        md.append("")
    con.close()
    out_path.write_text("\n".join(md), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description="產生 Python 專案 API 骨架地圖 (md+sqlite)")
    ap.add_argument("target", help="專案根目錄")
    ap.add_argument("-o", "--out", default="CODE_API_MAP.md")
    ap.add_argument("--db", default="code_structure.db")
    a = ap.parse_args()
    root = Path(a.target).resolve()
    if not root.is_dir():
        sys.exit(f"目錄不存在: {root}")
    out, db = Path(a.out).resolve(), Path(a.db).resolve()
    # 安全閘：輸出不准落在來源樹內（避免污染被掃描的專案）
    for p in (out, db):
        if str(p).lower().startswith(str(root).lower() + "\\"):
            sys.exit(f"拒絕：輸出 {p} 位於來源樹內，請指定樹外路徑")
    stats = compile_project(root, db)
    generate_map(db, out, root)
    print(f"{stats} -> {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
