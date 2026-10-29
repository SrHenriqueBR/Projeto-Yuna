import unittest
from voice_persona import select_installed_voice, preferred_voice_gender


VOICES = [
    {"name": "Voz A", "culture": "pt-BR", "gender": "Female", "enabled": True},
    {"name": "Voz B", "culture": "pt-BR", "gender": "Male", "enabled": True},
    {"name": "Voz C", "culture": "en-US", "gender": "Male", "enabled": True},
]


class VoicePersonaTests(unittest.TestCase):
    def test_feminine(self):
        self.assertEqual(select_installed_voice(VOICES, "feminina"), "Voz A")

    def test_masculine(self):
        self.assertEqual(select_installed_voice(VOICES, "masculina"), "Voz B")

    def test_unavailable_is_not_silently_substituted(self):
        self.assertIsNone(select_installed_voice(VOICES[:1], "masculina"))

    def test_neutral_uses_any_available_portuguese_voice(self):
        self.assertEqual(select_installed_voice(VOICES, "neutra"), "Voz A")

    def test_invalid_presentation(self):
        with self.assertRaises(ValueError):
            preferred_voice_gender("alien")
