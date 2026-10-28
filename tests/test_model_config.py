"""Yuna 0.26: configuração segura de modelo por computador."""
from pathlib import Path
import tempfile
import unittest

import model_config


class ModelSelectionTests(unittest.TestCase):
    def test_ram_recommendation(self):
        self.assertEqual(model_config.recommend_model(8), "qwen2.5:1.5b")
        self.assertEqual(model_config.recommend_model(8.5), "qwen2.5:1.5b")
        self.assertEqual(model_config.recommend_model(16), "qwen2.5:3b")
        self.assertEqual(model_config.recommend_model(None), "qwen2.5:3b")
        self.assertEqual(model_config.recommend_model(0), "qwen2.5:3b")
        self.assertEqual(model_config.recommend_model("invalido"), "qwen2.5:3b")

    def test_default_legacy_compatibility_and_manual_override(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.assertEqual(model_config.load_selected_model(root, {}), "qwen2.5:3b")
            model_config.save_selected_model(root, "qwen2.5:1.5b")
            self.assertEqual(model_config.load_selected_model(root, {}), "qwen2.5:1.5b")
            self.assertEqual(model_config.load_selected_model(
                root, {"YUNA_MODEL": "qwen2.5:7b"}), "qwen2.5:7b")

    def test_unsupported_file_contents_do_not_select_untrusted_model(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = model_config.model_path(root)
            path.parent.mkdir(parents=True)
            for invalid in ("qwen2.5:cloud", "malicious; command",
                            "../../secret", "custom:7b"):
                with self.subTest(value=invalid):
                    path.write_text(invalid, encoding="utf-8")
                    self.assertEqual(model_config.load_selected_model(root, {}),
                                     "qwen2.5:3b")
            path.write_text("qwen2.5:1.5b\n", encoding="utf-8-sig")
            self.assertEqual(model_config.load_selected_model(root, {}),
                             "qwen2.5:1.5b")

    def test_save_validation_and_preserves_other_data(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data = root / "data"
            data.mkdir()
            database = data / "yuna.db"
            database.write_bytes(b"MEMORIA-INTACTA")
            avatar = data / "avatar_yuna.json"
            avatar.write_text('{"hair":"preto"}', encoding="utf-8")
            for invalid in ("cloud", "qwen2.5:7b", "", "../hack", None):
                with self.subTest(invalid=invalid):
                    with self.assertRaises(ValueError):
                        model_config.save_selected_model(root, invalid)
            model_config.save_selected_model(root, "qwen2.5:1.5b")
            model_config.save_selected_model(root, "qwen2.5:3b")
            self.assertEqual(database.read_bytes(), b"MEMORIA-INTACTA")
            self.assertEqual(avatar.read_text(encoding="utf-8"),
                             '{"hair":"preto"}')
            self.assertEqual(model_config.load_selected_model(root, {}),
                             "qwen2.5:3b")
            self.assertEqual(list(data.glob("*.tmp")), [])

    def test_corrupt_config_falls_back_without_mutation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = model_config.model_path(root)
            path.parent.mkdir()
            path.write_bytes(b"\xff\xfe\xfe")
            self.assertEqual(model_config.load_selected_model(root, {}),
                             "qwen2.5:3b")
            self.assertEqual(path.read_bytes(), b"\xff\xfe\xfe")


if __name__ == "__main__":
    unittest.main()
