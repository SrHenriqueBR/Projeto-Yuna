"""Os testes funcionam sem Qt, Windows, TTS ou Ollama."""
import tempfile
import unittest
from pathlib import Path

from persona_preferences import PersonaPreferences
from persona_store import preference_path, load_preferences, save_preferences
from persona_commands import parse_voice_preference


class PersonaStoreTests(unittest.TestCase):
    def test_independent_operating_system_accounts(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            chosen = PersonaPreferences().updated(
                presentation="masculina", voice_style="suave")
            save_preferences(root, chosen, account="dominio\\pessoa_a")
            self.assertEqual(
                load_preferences(root, account="dominio\\pessoa_a"), chosen)
            self.assertEqual(load_preferences(root, account="dominio\\pessoa_b"),
                             PersonaPreferences())
            self.assertNotEqual(preference_path(root, "pessoa_a"),
                                preference_path(root, "pessoa_b"))

    def test_invalid_json_defaults_without_side_effect(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = preference_path(root, "user")
            path.parent.mkdir(parents=True)
            path.write_text("{broken", encoding="utf-8")
            self.assertEqual(load_preferences(root, "user"), PersonaPreferences())

    def test_rejects_invalid_preferences(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                save_preferences(folder, PersonaPreferences(
                    presentation="superuser"), "user")
            self.assertFalse(preference_path(folder, "user").exists())


class PersonaCommandsTests(unittest.TestCase):
    def test_natural_masculine_request(self):
        self.assertEqual(parse_voice_preference("Yuna, quero que vire homem"),
                         {"presentation": "masculina"})

    def test_feminine_and_style(self):
        self.assertEqual(
            parse_voice_preference("Mude sua voz para feminina e suave"),
            {"presentation": "feminina", "voice_style": "suave"})

    def test_voice_style_only(self):
        self.assertEqual(parse_voice_preference("Yuna, fale mais animada"),
                         {"voice_style": "energica"})

    def test_no_false_positive_for_general_question(self):
        self.assertIsNone(parse_voice_preference(
            "Yuna, me explique por que as vozes masculinas parecem mais graves"))
        self.assertIsNone(parse_voice_preference("A personagem vira homem no filme"))
        self.assertIsNone(parse_voice_preference(None))
