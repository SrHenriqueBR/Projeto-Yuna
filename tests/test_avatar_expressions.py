"""Yuna 0.23: comandos naturais e expressões visuais sem novas permissões."""
import importlib.util
import os
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import avatar_state
from avatar_motion import frame_at
import yuna

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
HAS_QT = importlib.util.find_spec("PySide6") is not None


class ExpressionIntentTests(unittest.TestCase):
    def test_natural_portuguese_requests(self):
        phrases = {
            "Yuna, pisca pra mim": "wink",
            "Yuna me dá uma piscadinha": "wink",
            "Yuna dá risada": "laugh",
            "Yuna ri para mim": "laugh",
            "Yuna fica tímida": "shy",
            "Yuna fica envergonhada": "shy",
            "Yuna vai dormir": "sleepy",
            "Yuna tira uma soneca": "sleepy",
            "Yuna acorda": "wake",
        }
        for request, expected in phrases.items():
            with self.subTest(request=request):
                self.assertEqual(avatar_state.parse_avatar_request(request),
                                 ("pose", expected))

    def test_negations_hypotheticals_and_unrelated_sentences(self):
        phrases = (
            "Yuna não vai dormir",
            "Yuna nunca dá risada",
            "E se eu pedir uma piscadinha?",
            "Como fazer a Yuna ficar tímida?",
            "Yuna talvez fique envergonhada",
            "Yuna dá risada e apaga meus arquivos",
            "Estou com sono, posso dormir?",
        )
        for phrase in phrases:
            with self.subTest(phrase=phrase):
                self.assertIsNone(avatar_state.parse_avatar_request(phrase))

    def test_poses_have_no_persistent_style_side_effects(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with patch.object(yuna, "ROOT", root):
                memory = yuna.Memory(root / "data" / "yuna.db")
                try:
                    for phrase in ("Yuna pisca pra mim", "Yuna dá risada",
                                   "Yuna fica tímida", "Yuna vai dormir",
                                   "Yuna acorda"):
                        with self.subTest(phrase=phrase):
                            with patch("yuna.ask_model", side_effect=AssertionError(
                                    "Expressive avatar must not contact Ollama")):
                                self.assertTrue(yuna.handle_message(memory, phrase))
                    self.assertFalse((root / "data" / "avatar_yuna.json").exists())
                    self.assertEqual(len(memory.history()), 10)
                finally:
                    memory.close()

    def test_sleepy_and_laugh_eyelids_are_closed(self):
        self.assertEqual(frame_at(15, "sleepy").blink, 1.0)
        self.assertEqual(frame_at(15, "laugh").blink, 1.0)
        self.assertEqual(frame_at(15, "idle").blink, 0.0)
        self.assertEqual(frame_at(15, "sleepy", reduced_motion=True).blink, 1.0)


@unittest.skipUnless(HAS_QT, "PySide6 opcional")
class ExpressionGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_new_poses_render_at_all_sizes_and_expire(self):
        from yuna_avatar import YunaAvatar
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            avatar = YunaAvatar(root)
            try:
                avatar.show()
                self.app.processEvents()
                for size in avatar_state.SIZES:
                    avatar_state.save_style(root, {
                        "size": size, "hair": "roxo", "walking": False
                    })
                    avatar.reload_appearance()
                    for pose in ("wink", "laugh", "shy", "sleepy"):
                        with self.subTest(size=size, pose=pose):
                            avatar.tick_count = 15
                            avatar.set_pose(pose, seconds=5)
                            self.app.processEvents()
                            self.assertEqual(avatar.visible_pose(), pose)
                            image = avatar.grab().toImage()
                            self.assertFalse(image.isNull())
                            factor = avatar_state.SIZES[size]
                            self.assertGreater(image.pixelColor(
                                round(95 * factor), round(135 * factor)).alpha(), 0)
                avatar.set_pose("sleepy", seconds=0)
                self.assertEqual(avatar.visible_pose(), "idle")
            finally:
                avatar.close()

    def test_explicit_expression_shows_while_speaking(self):
        from yuna_avatar import YunaAvatar
        with tempfile.TemporaryDirectory() as temp:
            avatar = YunaAvatar(Path(temp))
            try:
                avatar.set_speaking(True)
                avatar.set_pose("wink", seconds=4)
                self.assertEqual(avatar.visible_pose(), "wink")
                avatar.set_pose("laugh", seconds=4)
                self.assertEqual(avatar.visible_pose(), "laugh")
                avatar.set_speaking(False)
                avatar.set_pose("sleepy", seconds=0)
                self.assertIn(avatar.visible_pose(), ("idle", "walk"))
            finally:
                avatar.close()


if __name__ == "__main__":
    unittest.main()
