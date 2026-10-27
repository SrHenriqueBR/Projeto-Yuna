"""Yuna 0.21 — tests for actual cosmetic changes, poses and safe persistence."""
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import avatar_state
import yuna


class AvatarWardrobeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.project = patch.object(yuna, "ROOT", self.root)
        self.project.start()
        self.memory = yuna.Memory(self.root / "data" / "yuna.db")

    def tearDown(self):
        self.memory.close()
        self.project.stop()
        self.temp.cleanup()

    def test_all_new_customization_intents_without_slash_commands(self):
        cases = {
            "Yuna, deixa o cabelo curto": ("appearance", "hair_style", "curto"),
            "Yuna muda o cabelo para longo": ("appearance", "hair_style", "longo"),
            "Yuna faz duas maria-chiquinhas": ("appearance", "hair_style", "marias"),
            "Yuna, prende o cabelo em um rabo de cavalo": (
                "appearance", "hair_style", "rabo"),
            "Yuna, coloca uma tiara": ("appearance", "accessory", "tiara"),
            "Yuna usa óculos": ("appearance", "accessory", "oculos"),
            "Yuna, tira os óculos": ("appearance", "accessory", "nenhum"),
            "Yuna, coloca um casaco": ("appearance", "costume", "casaco"),
            "Yuna coloca a roupa casual": ("appearance", "costume", "casual"),
            "Yuna, usa vestido gótico": ("appearance", "costume", "vestido"),
            "Yuna acena pra mim": ("pose", "wave"),
            "Yuna, faz uma pose": ("pose", "pose"),
            "Yuna fica surpresa": ("pose", "surprised"),
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(avatar_state.parse_avatar_request(text), expected)

    def test_customizations_really_persist_and_keep_previous_colors(self):
        avatar_state.save_style(self.root, {
            "hair": "branco", "eyes": "azuis",
            "outfit": "clara", "walking": False
        })
        for text, key, value in (
            ("Yuna, deixa o cabelo curto", "hair_style", "curto"),
            ("Yuna, coloca um casaco", "costume", "casaco"),
            ("Yuna, usa óculos", "accessory", "oculos"),
            ("Yuna, tira os óculos", "accessory", "nenhum"),
        ):
            with self.subTest(text=text):
                with patch("yuna.ask_model",
                           side_effect=AssertionError("Avatar must be local")):
                    answer = yuna.handle_message(self.memory, text)
                self.assertTrue(answer.strip())
                self.assertEqual(avatar_state.load_style(self.root)[key], value)
        result = avatar_state.load_style(self.root)
        self.assertEqual(result["hair"], "branco")
        self.assertEqual(result["eyes"], "azuis")
        self.assertEqual(result["outfit"], "clara")
        self.assertFalse(result["walking"])
        self.assertEqual(len(self.memory.history()), 8)

    def test_old_avatar_json_migrates_without_losing_existing_preferences(self):
        old = {"hair": "ruivo", "eyes": "dourados",
               "outfit": "escura", "walking": False}
        avatar_state.save_style(self.root, old)
        loaded = avatar_state.load_style(self.root)
        for field, value in old.items():
            self.assertEqual(loaded[field], value)
        self.assertEqual(loaded["hair_style"], "longo")
        self.assertEqual(loaded["costume"], "vestido")
        self.assertEqual(loaded["accessory"], "laco")

    def test_invalid_styles_do_not_leak_into_saved_state(self):
        loaded = avatar_state.validated({
            "hair_style": "../Documents",
            "costume": {"danger": True},
            "accessory": "invalido",
            "walking": "False",
        })
        self.assertEqual(loaded["hair_style"], "longo")
        self.assertEqual(loaded["costume"], "vestido")
        self.assertEqual(loaded["accessory"], "laco")
        self.assertTrue(loaded["walking"])

    def test_hypothetical_and_negated_requests_do_not_mutate_avatar(self):
        for text in (
            "Como você ficaria de óculos?",
            "Não coloque uma tiara",
            "Se eu pedir para fazer uma pose, o que acontece?",
            "Yuna, talvez você deva usar o casaco",
            "Nunca mude seu cabelo para curto",
            "Estou pensando numa roupa casual para você",
        ):
            with self.subTest(text=text):
                self.assertIsNone(avatar_state.parse_avatar_request(text))
        self.assertFalse((self.root / "data" / "avatar_yuna.json").exists())

    def test_poses_are_ephemeral_and_leave_no_config(self):
        for message, gesture in (
            ("Yuna acena", "wave"),
            ("Yuna faz pose", "pose"),
            ("Yuna fica surpresa", "surprised"),
        ):
            with self.subTest(message=message):
                self.assertEqual(avatar_state.parse_avatar_request(message),
                                 ("pose", gesture))
                with patch("yuna.ask_model",
                           side_effect=AssertionError("No model needed")):
                    self.assertTrue(yuna.handle_message(self.memory, message))
        self.assertFalse((self.root / "data" / "avatar_yuna.json").exists())


@unittest.skipUnless(importlib.util.find_spec("PySide6"), "Qt optional")
class WardrobeRenderingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_visual_combinations_render_without_error(self):
        from yuna_avatar import YunaAvatar
        from avatar_state import save_style
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            avatar = YunaAvatar(root)
            try:
                avatar.show()
                self.app.processEvents()
                for hairstyle in avatar_state.HAIR_STYLES:
                    for costume in avatar_state.COSTUMES:
                        for accessory in avatar_state.ACCESSORIES:
                            with self.subTest(hair=hairstyle, costume=costume,
                                              accessory=accessory):
                                save_style(root, {
                                    "hair": "ruivo", "eyes": "azuis",
                                    "outfit": "escura",
                                    "hair_style": hairstyle,
                                    "costume": costume, "accessory": accessory,
                                    "walking": False,
                                })
                                avatar.reload_appearance()
                                avatar.tick_count = 18
                                avatar.set_pose("wave", 10)
                                self.app.processEvents()
                                image = avatar.grab().toImage()
                                self.assertFalse(image.isNull())
                                self.assertGreater(image.pixelColor(95, 135).alpha(), 0)
                for gesture in ("wave", "pose", "surprised"):
                    avatar.set_pose(gesture, 4)
                    self.app.processEvents()
                    self.assertEqual(avatar.visible_pose(), gesture)
            finally:
                avatar.close()


if __name__ == "__main__":
    unittest.main()
