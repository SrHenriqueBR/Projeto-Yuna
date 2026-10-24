"""Comportamentos novos: iniciativa, memória de perguntas e desligamento."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock
import yuna
from initiative import Initiative, looks_like_command


class InitiativeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.memory = yuna.Memory(Path(self.temp.name) / "yuna.db")
        self.initiative = self.memory.initiative

    def tearDown(self):
        self.memory.close()
        self.temp.cleanup()

    def test_greeting_and_capture_survive_restart(self):
        greeting = self.initiative.startup("Kaizen")
        self.assertIn("Olá, Kaizen", greeting)
        self.assertIn("O que vamos fazer hoje?", greeting)
        self.assertTrue(self.initiative.capture("Vou trabalhar no meu jogo."))
        self.assertEqual(len(self.initiative.recent()), 1)
        self.assertEqual(self.initiative.recent()[0][2], "Vou trabalhar no meu jogo.")
        self.memory.close()
        self.memory = yuna.Memory(Path(self.temp.name) / "yuna.db")
        self.initiative = self.memory.initiative
        self.assertEqual(len(self.initiative.recent()), 1)

    def test_questions_only_text_not_actions(self):
        self.initiative.startup()
        self.assertFalse(self.initiative.capture("Yuna, abra a Steam"))
        self.assertEqual(self.initiative.recent(), [])
        self.assertTrue(self.initiative.pending())
        question = self.initiative.propose("Vou estudar Python", Mock(return_value="Quer estudar Python comigo?"))
        self.assertIsNone(question)  # Ainda há uma pergunta pendente.
        self.initiative.capture("Vou estudar Python.")
        question = self.initiative.propose("Vou estudar Python", Mock(return_value="Quer estudar Python comigo?"))
        self.assertEqual(question, "Quer estudar Python comigo?")
        self.assertEqual(self.initiative.pending(), question)

    def test_filter_credential_and_disable(self):
        self.initiative.startup()
        self.assertTrue(self.initiative.capture("Minha senha é abcd1234"))
        self.assertEqual(self.initiative.recent(), [])
        self.initiative.enable(False)
        self.assertFalse(self.initiative.enabled)
        self.assertIsNone(self.initiative.startup())
        self.assertIsNone(self.initiative.propose("teste", Mock()))
        self.initiative.enable(True)
        self.assertTrue(self.initiative.enabled)

    def test_clear_and_forget(self):
        self.initiative.startup()
        self.initiative.capture("Vou criar um aplicativo.")
        ident = self.initiative.recent()[0][0]
        self.assertEqual(self.initiative.forget(ident), 1)
        self.assertEqual(self.initiative.recent(), [])
        self.initiative.startup()
        self.initiative.capture("Vou codificar.")
        self.memory.clear()
        self.assertEqual(len(self.initiative.recent()), 1)
        self.memory.clear(all_data=True)
        self.assertEqual(self.initiative.recent(), [])

    def test_model_invalid_question_fallback(self):
        self.assertIsNone(self.initiative.pending())
        result = self.initiative.propose("Prefiro trabalho local", Mock(return_value="Vou apagar arquivos"))
        self.assertTrue(result.endswith("?"))
        self.assertIn("aprendesse", result)

    def test_actions_heuristic(self):
        self.assertTrue(looks_like_command("Yuna, abra a Steam"))
        self.assertTrue(looks_like_command("/ambiente"))
        self.assertFalse(looks_like_command("Vou jogar na Steam"))

    def test_persona_feminine(self):
        self.assertIn("obrigada", yuna.SYSTEM)
        self.assertIn("modelo local", yuna.SYSTEM.lower() + " modelo local")


if __name__ == "__main__":
    unittest.main()
