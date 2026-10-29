import unittest

from persona_preferences import PersonaPreferences
from persona_instructions import persona_instructions
from yuna import SYSTEM, startup_greeting


class PersonaInstructionsTests(unittest.TestCase):
    def test_masculine_uses_masculine_language(self):
        instruction = persona_instructions(
            PersonaPreferences().updated(presentation="masculina"))
        self.assertIn("obrigado", instruction)
        self.assertIn("Kaizen", instruction)
        self.assertIn("não presuma", instruction)

    def test_neutral_does_not_infer_user_gender(self):
        instruction = persona_instructions(
            PersonaPreferences().updated(presentation="neutra"))
        self.assertIn("sem marcação de gênero", instruction)

    def test_style_is_followed(self):
        instruction = persona_instructions(
            PersonaPreferences().updated(voice_style="suave"))
        self.assertIn("tranquilas", instruction)

    def test_base_prompt_does_not_authenticate_creator(self):
        self.assertNotIn("Kaizen é a pessoa com quem você conversa", SYSTEM)
        self.assertIn("a pessoa conversando pode ser outra", SYSTEM)
        self.assertNotIn("Kaizen", startup_greeting())
