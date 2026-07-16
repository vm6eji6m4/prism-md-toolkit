# -*- coding: utf-8 -*-
"""
txt2md_copy.py — 安全版 TXT→MD 知識庫轉檔器（只複製、永不就地改名、永不刪原檔）
源自 Antigravity txt_to_md_copier 概念；07-15 全槽事故後由 Claude 重寫加安全閘。

用途：把 .txt 素材（LINE 匯出、逐字稿、會議紀錄）轉成帶標題頭的 .md 副本，
餵 Obsidian vault / PRISM 打包 / claude-mem 建庫。原始樹一個位元組都不動。

用法：
  py -3.11 txt2md_copy.py <來源目錄> <輸出目錄> [--dry-run]
輸出目錄必須在來源樹之外；預設 dry-run 列清單，加 --run 才真寫。
"""
import argparse
import sys
from pathlib import Path

SKIP_DIRS = {".venv", "venv", "node_modules", "__pycache__", ".git",
             "dist", "build", "runtime", ".dtrash", "$recycle.bin",
             "system volume information", ".archive", ".quarantine"}


def convert(src_root: Path, out_root: Path, run: bool) -> dict:
    stats = {"converted": 0, "skipped_dir": 0, "errors": 0}
    for p in sorted(src_root.rglob("*")):
        if not p.is_file() or p.suffix.lower() != ".txt":
            continue
        rel = p.relative_to(src_root)
        if any(part.lower() in SKIP_DIRS for part in rel.parts):
            stats["skipped_dir"] += 1
            continue
        dst = (out_root / rel).with_suffix(".md")
        try:
            if run:
                dst.parent.mkdir(parents=True, exist_ok=True)
                content = p.read_text(encoding="utf-8", errors="ignore")
                body = (f"```text\n{content}\n```\n"
                        if len(content.splitlines()) > 100 else content)
                dst.write_text(f"# {p.name}\n\n> 來源：`{p}`\n\n{body}", encoding="utf-8")
            else:
                print(f"[DRY] {rel} -> {dst}")
            stats["converted"] += 1
        except Exception as e:  # noqa: BLE001
            stats["errors"] += 1
            print(f"ERROR {p}: {e}", file=sys.stderr)
    return stats


def main():
    ap = argparse.ArgumentParser(description="TXT→MD 複製式轉檔（永不動原檔）")
    ap.add_argument("source")
    ap.add_argument("output")
    ap.add_argument("--run", action="store_true", help="真的寫檔（預設 dry-run）")
    a = ap.parse_args()
    src, out = Path(a.source).resolve(), Path(a.output).resolve()
    if not src.is_dir():
        sys.exit(f"來源不存在: {src}")
    # 安全閘 1：輸出不准在來源樹內
    if str(out).lower().startswith(str(src).lower() + "\\") or out == src:
        sys.exit("拒絕：輸出目錄在來源樹內")
    # 安全閘 2：來源禁止整顆磁碟根（根目錄的 parent 是自己）
    if src.parent == src:
        sys.exit("拒絕：不接受磁碟根目錄當來源（07-15 全槽事故教訓）")
    stats = convert(src, out, a.run)
    print(f"[{'RUN' if a.run else 'DRY-RUN'}] {stats}")


if __name__ == "__main__":
    main()
