# -*- coding: utf-8 -*-
"""零依賴測試套件（unittest，標準庫即可跑）：
    python -m unittest discover tests -v
涵蓋 2026-07-17 外審 TOP3：路徑安全閘、無參數行為、表格污染防線，
外加 token 估算 CJK 下限與 txt2md 安全語意。負對照原則：每道閘都要證明「會正確拒絕」。
"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "prism"))
sys.path.insert(0, str(REPO / "tools"))

import splitter  # noqa: E402
import prism_pack  # noqa: E402
import txt2md_copy  # noqa: E402
import code_api_map  # noqa: E402

PY = sys.executable


class TestHeadingGuard(unittest.TestCase):
    """T3 表格污染防線（llm_survey 實案：45 片 → 16 片）"""

    def test_rejects_table_rows(self):
        for junk in ("1024 TPU v3", "512 TPU v4", "2048 Ascend 910", "800 GPU"):
            self.assertFalse(splitter.looks_like_real_heading(junk), junk)

    def test_accepts_real_headings(self):
        for ok in ("Methodology", "研究方法", "摘要",
                   "2 The notion of a derived scheme", "Results"):
            self.assertTrue(splitter.looks_like_real_heading(ok), ok)

    def test_split_drops_table_sections(self):
        md = "\n".join(["# Introduction", "text", "## 1024 TPU v3",
                        "- row", "## Conclusion", "done"])
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "p.md"
            src.write_text(md, encoding="utf-8")
            out = Path(td) / "slices"
            files = splitter.split_markdown_paper(src, out)
            names = " ".join(f.name for f in files)
            self.assertNotIn("TPU", names)
            self.assertIn("Conclusion", names)


class TestIsWithin(unittest.TestCase):
    """T1 嚴格層級判定（三支工具同一實作，各自驗）"""

    def _check(self, fn):
        self.assertTrue(fn(r"D:\a\b\c.txt", r"D:\a"))
        self.assertFalse(fn(r"D:\ab", r"D:\a"))          # 前綴字串陷阱
        self.assertFalse(fn(r"C:\x", r"D:\x"))            # 跨磁碟
        self.assertFalse(fn(r"D:\a", r"D:\a\b"))          # 方向反了

    def test_all_three_tools(self):
        for mod in (prism_pack, txt2md_copy, code_api_map):
            self._check(mod.is_within)


class TestTokenEstimate(unittest.TestCase):
    """W1：CJK fallback 不得退回英文換算率（len//4）"""

    def test_cjk_floor(self):
        zh = "佛堂影片語意檢索站" * 20  # 180 個中文字
        est = prism_pack.estimate_tokens(zh)
        self.assertGreaterEqual(est, len(zh) // 2)  # 遠高於 len//4


class TestCliGates(unittest.TestCase):
    """T2 無參數行為＋端對端負對照（subprocess）"""

    def test_prism_pack_no_args_prints_usage(self):
        r = subprocess.run([PY, str(REPO / "prism" / "prism_pack.py")],
                           capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 1)
        self.assertIn("用法", r.stdout + r.stderr)

    def test_txt2md_refuses_drive_root(self):
        # 來源=磁碟根時兩道閘擇一必攔：輸出必在同槽（樹內閘）或先觸磁碟根閘
        r = subprocess.run([PY, str(REPO / "tools" / "txt2md_copy.py"),
                            os.path.splitdrive(str(REPO))[0] + "\\", str(REPO / "_x")],
                           capture_output=True, text=True, timeout=30)
        self.assertNotEqual(r.returncode, 0)
        combined = r.stdout + r.stderr
        self.assertTrue("磁碟根" in combined or "來源樹內" in combined, combined)

    def test_txt2md_refuses_in_tree_output(self):
        with tempfile.TemporaryDirectory() as td:
            r = subprocess.run([PY, str(REPO / "tools" / "txt2md_copy.py"),
                                td, str(Path(td) / "sub")],
                               capture_output=True, text=True, timeout=30)
            self.assertNotEqual(r.returncode, 0)

    def test_txt2md_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "src"
            src.mkdir()
            (src / "a.txt").write_text("hi", encoding="utf-8")
            out = Path(td) / "out"
            subprocess.run([PY, str(REPO / "tools" / "txt2md_copy.py"),
                            str(src), str(out)],
                           capture_output=True, text=True, timeout=30)
            self.assertFalse(out.exists())  # 預設 dry-run：不落盤

    def test_code_api_map_refuses_in_tree_output(self):
        r = subprocess.run([PY, str(REPO / "tools" / "code_api_map.py"),
                            str(REPO), "-o", str(REPO / "MAP.md")],
                           capture_output=True, text=True, timeout=30)
        self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
