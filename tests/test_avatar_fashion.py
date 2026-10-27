"""Yuna 0.21 — cabelo/roupa/acessórios em camadas e gestos naturais."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import importlib.util

import avatar_state
import yuna

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class FashionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.root_patch = patch.object(yuna, "ROOT", self.root)
        self.root_patch.start()
        self.memory = yuna.Memory(self.root / "data" / "yuna.db")

    def tearDown(self):
        self.memory.close()
        self.root_patch.stop()
        self.temp.cleanup()

    def test_old_style_file_migrates_without_losing_colours_or_walk(self):
        old = self.root / "data" / "avatar_yuna.json"
        old.write_text(json.dumps(
            {"hair": "branco", "eyes": "azuis",
             "outfit": "clara", "walking": False}
        ), encoding="utf-8")
        style = avatar_state.load_style(self.root)
        self.assertEqual(style["hair"], "branco")
        self.assertEqual(style["eyes"], "azuis")
        self.assertEqual(style["outfit"], "clara")
        self.assertFalse(style["walking"])
        self.assertEqual(style["hair_style"], "longo")
        self.assertEqual(style["costume"], "vestido")
        self.assertEqual(style["accessory"], "laco")

    def test_explicit_fashion_requests_without_llm(self):
        cases = [
            ("Yuna, deixa o cabelo curto", "hair_style", "curto"),
            ("Yuna, muda o cabelo longo", "hair_style", "longo"),
            ("Yuna, faz duas maria-chiquinhas", "hair_style", "marias"),
            ("Yuna, prende o cabelo em um rabo de cavalo", "hair_style", "rabo"),
            ("Yuna, usa vestido gótico", "costume", "vestido"),
            ("Yuna, coloca a roupa casual", "costume", "casual"),
            ("Yuna, coloca um casaco", "costume", "casaco"),
            ("Yuna, coloca um laço", "accessory", "laco"),
            ("Yuna, coloca uma tiara", "accessory", "tiara"),
            ("Yuna, usa óculos", "accessory", "oculos"),
            ("Yuna, tira os óculos", "accessory", "nenhum"),
        ]
        for utterance, field, expected in cases:
            with self.subTest(utterance=utterance):
                self.assertEqual(
                    avatar_state.parse_avatar_request(utterance),
                    ("appearance", field, expected))
                with patch("yuna.ask_model",
                           side_effect=AssertionError("Não chamar Ollama")):
                    reply = yuna.handle_message(self.memory, utterance)
                self.assertTrue(reply.strip())
                self.assertEqual(avatar_state.load_style(self.root)[field], expected)

    def test_gestures_are_local_without_ai_and_no_memory_rewrite(self):
        memory_path = self.root / "data" / "yuna.db"
        for phrase, action in [
            ("Yuna, acena pra mim", "wave"),
            ("Yuna, dá tchau", "wave"),
            ("Yuna, faz uma pose", "pose"),
            ("Yuna, fica surpresa", "surprised"),
        ]:
            with self.subTest(phrase=phrase):
                self.assertEqual(
                    avatar_state.parse_avatar_request(phrase), ("pose", action))
                with patch("yuna.ask_model",
                           side_effect=AssertionError("Não chamar Ollama")):
                    yuna.handle_message(self.memory, phrase)
        self.assertTrue(memory_path.is_file())

    def test_negations_hypotheses_unknown_styles_cannot_change_state(self):
        for phrase in [
            "Como deixar o cabelo curto?",
            "Não coloca óculos",
            "Se eu falar Yuna usa óculos, o que acontece?",
            "Talvez fique com cabelo longo",
            "Eu gostei do vestido",
            "Yuna, não tira a tiara",
            "Yuna, coloca malware no computador",
            "Yuna, usa um traje futurista feito de arquivos locais",
        ]:
            with self.subTest(phrase=phrase):
                self.assertIsNone(avatar_state.parse_avatar_request(phrase))
        self.assertFalse((self.root / "data" / "avatar_yuna.json").exists())

    def test_invalid_saved_keys_do_not_enable_unknown_assets(self):
        avatar_state.save_style(self.root, {
            "hair_style": "../../../../",
            "costume": "script.py",
            "accessory": "C:\\Windows",
            "walking": "yes",
        })
        style = avatar_state.load_style(self.root)
        self.assertEqual(style["hair_style"], "longo")
        self.assertEqual(style["costume"], "vestido")
        self.assertEqual(style["accessory"], "laco")
        self.assertTrue(style["walking"])


@unittest.skipUnless(importlib.util.find_spec("PySide6") is not None,
                     "PySide6 não disponível")
class FashionRenderingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_real_different_hair_outfit_and_accessory_renderings(self):
        from yuna_avatar import YunaAvatar
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            avatar = YunaAvatar(root)
            try:
                avatar.show()
                avatar.tick_count = 20
                self.app.processEvents()

                def image_fingerprint(style):
                    avatar_state.save_style(root, style)
                    avatar.reload_appearance()
                    self.app.processEvents()
                    screenshot = avatar.grab().toImage()
                    self.assertFalse(screenshot.isNull())
                    return tuple(screenshot.pixel(x, y)
                                 for y in range(62, 240, 7)
                                 for x in range(20, 170, 7))

                start = avatar_state.DEFAULTS.copy()
                start["walking"] = False
                basic = image_fingerprint(start)
                for field, options in (
                    ("hair_style", ("curto", "marias", "rabo")),
                    ("costume", ("casual", "casaco")),
                    ("accessory", ("nenhum", "tiara", "oculos")),
                ):
                    for option in options:
                        with self.subTest(feature=field, option=option):
                            style = dict(start)
                            style[field] = option
                            self.assertNotEqual(image_fingerprint(style), basic)
                for pose in ("wave", "pose", "surprised"):
                    avatar.set_pose(pose, 5)
                    self.assertEqual(avatar.visible_pose(), pose)
                    self.app.processEvents()
            finally:
                avatar.close()


if __name__ == "__main__":
    unittest.main()
