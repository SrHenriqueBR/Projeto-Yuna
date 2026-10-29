import unittest
from persona_preferences import PersonaPreferences, creator_statement
from emergency_stop import EmergencyStop, is_stop_request


class PersonaAndStopTests(unittest.TestCase):
    def test_switch_presentation_without_changing_creator(self):
        persona = PersonaPreferences().updated(presentation="masculina", voice_style="suave")
        self.assertEqual(persona.presentation, "masculina")
        self.assertEqual(persona.voice_style, "suave")
        self.assertIn("Kaizen", creator_statement())

    def test_reject_invalid_preferences(self):
        with self.assertRaises(ValueError):
            PersonaPreferences().updated(presentation="desconhecida")

    def test_stop_phrase_is_case_insensitive(self):
        self.assertTrue(is_stop_request("BREAK080111"))
        self.assertTrue(is_stop_request("Yuna, parar agora".replace(",", "")))
        self.assertFalse(is_stop_request("Vou escrever break080111 num arquivo"))

    def test_stop_token(self):
        stop = EmergencyStop()
        stop.stop()
        with self.assertRaises(InterruptedError):
            stop.check()
        stop.reset()
        stop.check()
