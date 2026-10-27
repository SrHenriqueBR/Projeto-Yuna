"""Yuna 0.19: avatar 2D leve, personalização local e limites de intenção."""
import ast
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import avatar_state
import yuna


class AvatarStateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.memory = yuna.Memory(self.root / "data" / "yuna.db")

    def tearDown(self):
        self.memory.close()
        self.tmp.cleanup()

    def test_all_appearance_defaults(self):
        state = avatar_state.load_style(self.root)
        self.assertEqual(state["hair"], "preto")
        self.assertEqual(state["eyes"], "vermelhos")
        self.assertTrue(state["walking"])
        self.assertFalse((self.root / "data" / "avatar_yuna.json").exists())

    def test_normal_hair_changes_are_persisted(self):
        for statement, color in (
            ("Yuna, muda o cabelo para branco", "branco"),
            ("Yuna muda seu cabelo pra ruivo", "ruivo"),
            ("Yuna troca o cabelo por preto", "preto"),
            ("Yuna, pinta o cabelo de roxo", "roxo"),
        ):
            with self.subTest(statement=statement):
                parsed = avatar_state.parse_avatar_request(statement)
                self.assertEqual(parsed, ("appearance", "hair", color))
                with patch("yuna.ask_model", side_effect=AssertionError("Do not use model")):
                    answer = yuna.handle_message(self.memory, statement)
                self.assertIn("Mudei meu cabelo", answer)
                self.assertEqual(avatar_state.load_style(self.root)["hair"], color)

    def test_eyes_outfit_and_natural_commands(self):
        for phrase, key, value in (
            ("Yuna, muda os olhos para azuis", "eyes", "azuis"),
            ("Yuna, troca o olho para vermelho", "eyes", "vermelhos"),
            ("Yuna, coloca a roupa preta", "outfit", "escura"),
            ("Yuna, deixa a roupa clara", "outfit", "clara"),
        ):
            with self.subTest(phrase=phrase):
                result = avatar_state.parse_avatar_request(phrase)
                self.assertEqual(result, ("appearance", key, value))

    def test_states_walk_sit_happy_angry_and_stop(self):
        for phrase, expected in (
            ("Yuna senta", "sit"),
            ("Yuna fica chateada", "sit"),
            ("Yuna levanta", "stand"),
            ("Yuna fica brava", "angry"),
            ("Yuna fica feliz", "happy"),
            ("Yuna pare de andar", "stop"),
            ("Yuna anda pela tela", "walk"),
        ):
            with self.subTest(phrase=phrase):
                self.assertEqual(avatar_state.parse_avatar_request(phrase), ("pose", expected))
        yuna.handle_message(self.memory, "Yuna pare de andar")
        self.assertFalse(avatar_state.load_style(self.root)["walking"])
        yuna.handle_message(self.memory, "Yuna anda pela tela")
        self.assertTrue(avatar_state.load_style(self.root)["walking"])

    def test_does_not_mutate_from_questions_negations_or_long_text(self):
        for phrase in (
            "Como mudar o cabelo da Yuna?", "Não muda o cabelo para branco",
            "Se eu disser Yuna muda o cabelo para branco funciona?",
            "Eu gosto de cabelos brancos", "Yuna, talvez pinte o cabelo",
            "Yuna, por que o cabelo está preto?", "Yuna, me ajuda com Python",
        ):
            with self.subTest(phrase=phrase):
                self.assertIsNone(avatar_state.parse_avatar_request(phrase))
        self.assertFalse((self.root / "data" / "avatar_yuna.json").exists())

    def test_rejects_unknown_style_and_does_not_modify_old_data(self):
        original = self.root / "data" / "yuna.db"
        baseline = original.read_bytes()
        style = avatar_state.validated({
            "hair": "../segredo", "eyes": "vermelhos",
            "outfit": "escura", "walking": "True"
        })
        self.assertEqual(style["hair"], "preto")
        self.assertTrue(style["walking"])
        self.assertIsNone(avatar_state.parse_avatar_request("Yuna muda cabelo para arcoiris"))
        # Changing appearance never alters the original SQLite database.
        avatar_state.save_style(self.root, style)
        self.assertEqual(original.read_bytes(), baseline)

    def test_ui_integrates_controller_and_show_hide(self):
        root = Path(__file__).resolve().parents[1]
        gui = (root / "yuna_desktop.py").read_text(encoding="utf-8")
        renderer = (root / "yuna_avatar.py").read_text(encoding="utf-8")
        ast.parse(renderer)
        self.assertIn("class YunaAvatar(QWidget)", renderer)
        self.assertIn("def paintEvent(self, event):", renderer)
        self.assertIn("def advance(self):", renderer)
        self.assertIn("def mousePressEvent(self, event):", renderer)
        self.assertIn("self.avatar_button.clicked.connect(self.toggle_avatar)", gui)
        self.assertIn("self.avatar_window.reload_appearance()", gui)
        self.assertIn("parse_avatar_request(content)", gui)

    def test_gui_offscreen_actual_avatar_widget(self):
        from PySide6.QtWidgets import QApplication
        from yuna_avatar import YunaAvatar
        app = QApplication.instance() or QApplication([])
        avatar = YunaAvatar(self.root)
        try:
            avatar.show()
            app.processEvents()
            self.assertTrue(avatar.isVisible())
            avatar.set_pose("sit", 5)
            self.assertEqual(avatar.visible_pose(), "sit")
            avatar.set_pose("angry", 5, "Ei!")
            self.assertEqual(avatar.visible_pose(), "angry")
            avatar_state.save_style(self.root, {
                "hair": "branco", "eyes": "azuis",
                "outfit": "clara", "walking": False
            })
            avatar.reload_appearance()
            self.assertEqual(avatar.appearance["hair"], "branco")
            self.assertFalse(avatar.appearance["walking"])
            avatar.advance()
            app.processEvents()
        finally:
            avatar.close()


if __name__ == "__main__":
    unittest.main()
