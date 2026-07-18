# -*- coding: utf-8 -*-
"""--skill 模式測試（unittest，標準庫即可跑）：
    python -m unittest tests.test_skill_pack -v
負對照原則：密鑰閘與樹內輸出閘都要證明「會正確拒絕」。
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "prism"))

import skill_pack  # noqa: E402


def make_corpus(root: Path):
    (root / "README.md").write_text("# Demo\n\nEntry point doc.\n", encoding="utf-8")
    (root / "core.py").write_text("def hello():\n    return 1\n", encoding="utf-8")
    sub = root / "docs"
    sub.mkdir()
    (sub / "guide.md").write_text("## Guide\n\nHow to use.\n", encoding="utf-8")


class TestSkillPackLayout(unittest.TestCase):
    def test_builds_skill_folder(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "corpus"
            src.mkdir()
            make_corpus(src)
            out = Path(td) / "out"
            skill_dir = skill_pack.build_skill(src, out, log=lambda *_: None)

            self.assertTrue((skill_dir / "SKILL.md").exists())
            self.assertTrue((skill_dir / "manifest.json").exists())
            refs = list((skill_dir / "references").iterdir())
            self.assertEqual(len(refs), 3)

            text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
            # frontmatter：只允許標準欄位（二審裁定：拒自創 triggers 等欄位）
            fm = text.split("---")[1]
            self.assertIn("name:", fm)
            self.assertIn("description:", fm)
            self.assertNotIn("triggers", fm)
            # 三段固定結構：守則 → Ledger（前置）→ 地圖
            self.assertIn("## 1. Reading rules", text)
            self.assertIn("## 2. Reading Ledger", text)
            self.assertIn("## 3. Map", text)
            self.assertLess(text.index("Reading Ledger"), text.index("## 3. Map"))
            # 原則句取代魔數（二審裁定）
            self.assertIn("minimum files needed", text)

    def test_manifest_integrity_fields(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "corpus"
            src.mkdir()
            make_corpus(src)
            skill_dir = skill_pack.build_skill(src, Path(td) / "out", log=lambda *_: None)
            manifest = json.loads((skill_dir / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["total_files"], 3)
            for f in manifest["files"]:
                self.assertEqual(len(f["sha256"]), 64)
                self.assertIn(f["level"], ("required", "important", "optional", "reference", "archive"))
                # references/ 裡的實體檔要真的存在
                self.assertTrue((skill_dir / "references" / f["ref"]).exists())


class TestSecretGate(unittest.TestCase):
    """負對照：埋一把假金鑰，證明會被攔下且不進 references/。"""

    def test_planted_secret_is_excluded(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "corpus"
            src.mkdir()
            make_corpus(src)
            leaked = "token = \"ghp_" + "A" * 36 + "\"\n"
            (src / "leaky.py").write_text(leaked, encoding="utf-8")

            skill_dir = skill_pack.build_skill(src, Path(td) / "out", log=lambda *_: None)
            refs = [p.name for p in (skill_dir / "references").iterdir()]
            self.assertFalse(any("leaky" in r for r in refs), "洩密檔不得進 references/")
            manifest = json.loads((skill_dir / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(len(manifest["excluded_secret_suspects"]), 1)
            self.assertEqual(manifest["excluded_secret_suspects"][0]["path"], "leaky.py")
            self.assertIn("github-token", manifest["excluded_secret_suspects"][0]["patterns"])

    def test_clean_corpus_excludes_nothing(self):
        """反向負對照：乾淨語料不得誤殺（防空檢查冒充真檢查的鏡像）。"""
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "corpus"
            src.mkdir()
            make_corpus(src)
            skill_dir = skill_pack.build_skill(src, Path(td) / "out", log=lambda *_: None)
            manifest = json.loads((skill_dir / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["excluded_secret_suspects"], [])


class TestOutputGate(unittest.TestCase):
    """負對照：輸出落在來源樹內必須拒絕（全工具箱鐵律）。"""

    def test_in_tree_output_refused(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "corpus"
            src.mkdir()
            make_corpus(src)
            with self.assertRaises(ValueError):
                skill_pack.build_skill(src, src / "nested_out", log=lambda *_: None)

    def test_unknown_template_refused(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "corpus"
            src.mkdir()
            make_corpus(src)
            with self.assertRaises(ValueError):
                skill_pack.build_skill(src, Path(td) / "out", template="nope", log=lambda *_: None)


class TestLedgerVerification(unittest.TestCase):
    """負對照：模型捏造「讀過但沒供給」的檔，機器驗證必須抓到（A/B 複測實案）。"""

    def test_fabricated_claim_detected(self):
        answer = ("C1. 語料中沒有此資訊。\n### Reading Ledger\n"
                  "- Read:\n  - references/045_reference_GOTCHAS.md (reference, 31,117 tokens)\n")
        served = ["001_required_README.md", "038_optional_station__app.py"]
        v = skill_pack.verify_ledger(answer, served)
        self.assertTrue(v["ledger_present"])
        self.assertIn("045_reference_GOTCHAS.md", v["fabricated"])

    def test_honest_claim_passes(self):
        answer = ("D1. 口訣是關鎖掛洩測修。\n### Reading Ledger\n"
                  "- Read:\n  - references/001_required_README.md (required, 900 tokens)\n")
        v = skill_pack.verify_ledger(answer, ["001_required_README.md"])
        self.assertEqual(v["fabricated"], [])

    def test_missing_ledger_reported(self):
        v = skill_pack.verify_ledger("答案而已，沒附台帳。", ["001_required_README.md"])
        self.assertFalse(v["ledger_present"])


class TestEvidenceTemplate(unittest.TestCase):
    def test_evidence_rules_stricter(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "corpus"
            src.mkdir()
            make_corpus(src)
            skill_dir = skill_pack.build_skill(src, Path(td) / "out",
                                               template="evidence", log=lambda *_: None)
            text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("path:line-range", text)
            self.assertIn("at most 5 files", text)


if __name__ == "__main__":
    unittest.main()
