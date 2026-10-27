"""Yuna 0.22: avatar escalável, preferências locais e regressões da interface."""
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import avatar_state
import yuna

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class AvatarSizeStateTests(unittest.TestCase):
    def test_default_and_legacy_data(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.assertEqual(avatar_state.load_style(root)["size"], "normal")
            avatar_state.save_style(root, {"hair": "ruivo", "walking": False})
            state = avatar_state.load_style(root)
            self.assertEqual(state["size"], "normal")
            self.assertEqual(state["hair"], "ruivo")
            self.assertFalse(state["walking"])

    def test_natural_size_requests(self):
        cases = {
            "Yuna fica pequena": "pequena",
            "Yuna, muda seu tamanho pra grande": "grande",
            "Yuna ajusta o tamanho para pequeno": "pequena",
            "Yuna, deixa o avatar normal": "normal",
            "Yuna fica grande": "grande",
        }
        for phrase, choice in cases.items():
            with self.subTest(phrase=phrase):
                self.assertEqual(avatar_state.parse_avatar_request(phrase),
                                 ("appearance", "size", choice))

    def test_negated_or_hypothetical_requests_not_acted_on(self):
        for phrase in (
            "Yuna, não fica grande",
            "Como faço para a Yuna ficar pequena?",
            "Se eu disser muda seu tamanho pra grande?",
            "Talvez deixa o avatar normal",
        ):
            with self.subTest(phrase=phrase):
                self.assertIsNone(avatar_state.parse_avatar_request(phrase))

    def test_size_persists_without_changing_existing_look_or_memory(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            avatar_state.save_style(root, {
                "hair": "branco", "eyes": "azuis", "outfit": "escura",
                "walking": False, "hair_style": "marias",
            })
            with patch.object(yuna, "ROOT", root):
                memory = yuna.Memory(root / "data" / "yuna.db")
                try:
                    with patch("yuna.ask_model", side_effect=AssertionError("no LLM")):
                        response = yuna.handle_message(memory, "Yuna fica grande")
                    self.assertIn("maior", response.lower())
                    style = avatar_state.load_style(root)
                    self.assertEqual(style["size"], "grande")
                    self.assertEqual(style["hair"], "branco")
                    self.assertEqual(style["eyes"], "azuis")
                    self.assertEqual(style["hair_style"], "marias")
                    self.assertFalse(style["walking"])
                finally:
                    memory.close()

    def test_invalid_size_is_rejected(self):
        self.assertEqual(avatar_state.validated({"size": "../../x"})["size"], "normal")
        self.assertEqual(avatar_state.validated({"size": 5})["size"], "normal")


@unittest.skipUnless(importlib.util.find_spec("PySide6"), "Qt optional")
class AvatarSizeRenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_three_sizes_render_and_keep_existing_poses(self):
        from yuna_avatar import YunaAvatar
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            avatar = YunaAvatar(root)
            try:
                avatar.show()
                self.app.processEvents()
                for key, factor in avatar_state.SIZES.items():
                    with self.subTest(size=key):
                        avatar_state.save_style(root, {"size": key, "walking": False})
                        avatar.reload_appearance()
                        avatar.set_pose("wave", seconds=4)
                        self.app.processEvents()
                        self.assertEqual(avatar.width(), round(190 * factor))
                        self.assertEqual(avatar.height(), round(277 * factor))
                        self.assertEqual(avatar.visible_pose(), "wave")
                        picture = avatar.grab().toImage()
                        self.assertFalse(picture.isNull())
                        self.assertGreater(picture.pixelColor(
                            round(95 * factor), round(135 * factor)).alpha(), 0)
            finally:
                avatar.close()


if __name__ == "__main__":
    unittest.main()
