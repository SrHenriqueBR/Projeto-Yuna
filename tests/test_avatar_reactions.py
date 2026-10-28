import unittest
from avatar_reactions import reaction_for_text


class ReactionTests(unittest.TestCase):
    def test_greeting_and_laughter(self):
        self.assertEqual(reaction_for_text("Olá, Kaizen!"), ("wave", "happy"))
        self.assertEqual(reaction_for_text("Hahaha, boa!"), ("laugh", "happy"))

    def test_private_or_empty_does_not_trigger(self):
        self.assertIsNone(reaction_for_text("Olá", private=True))
        self.assertIsNone(reaction_for_text(""))
        self.assertIsNone(reaction_for_text(None))

    def test_neutral_text_does_not_force_gesture(self):
        self.assertIsNone(reaction_for_text("O arquivo foi salvo na pasta."))
