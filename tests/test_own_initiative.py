"""Yuna chooses and performs her own bounded activities, without random chores."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import yuna
from initiative import looks_like_command
from own_initiative import (
    is_asking_yuna_to_choose, is_authorization, is_rejection,
    propose_own_activity, pending_own_activity, clear_own_activity,
)


class OwnInitiativeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.memory = yuna.Memory(Path(self.temp.name) / "data" / "yuna.db")

    def tearDown(self):
        self.memory.close()
        self.temp.cleanup()

    def test_question_variants_choose_one_activity_without_model(self):
        for text in (
            "Yuna, o que você quer fazer?",
            "O que voce quer fazer?",
            "Você gostaria de fazer o que?",
            "Yuna, tem algo que você queira fazer?",
        ):
            self.assertTrue(is_asking_yuna_to_choose(text), text)
        self.assertFalse(is_asking_yuna_to_choose("Estou falando sobre o que você quer fazer"))
        self.assertFalse(is_asking_yuna_to_choose("Faça o que quiser no meu computador"))

    def test_proposal_not_offloaded_to_user_or_immediately_written(self):
        with patch("yuna.ask_model", side_effect=AssertionError("No model required")):
            reply = yuna.handle_message(self.memory, "Yuna, o que você quer fazer?")
        self.assertIn("Quero escrever", reply)
        self.assertIn("vou cuidar da escrita", reply)
        self.assertEqual(pending_own_activity(self.memory.initiative), "diario")
        self.assertFalse((self.memory.folder / "diario_yuna.md").exists())

    def test_confirmation_creates_entry_and_saves_in_local_data(self):
        yuna.handle_message(self.memory, "O que você quer fazer?")
        content = ("Hoje vou pensar em maneiras de explicar melhor os projetos, "
                   "organizar tarefas pequenas e apresentar resultados de forma clara.")
        with patch("yuna.generate_entry", return_value=content) as generate:
            result = yuna.handle_message(self.memory, "Pode fazer")
        generate.assert_called_once()
        self.assertIn("salvei", result)
        self.assertEqual(pending_own_activity(self.memory.initiative), None)
        saved = (self.memory.folder / "diario_yuna.md").read_text(encoding="utf-8")
        self.assertIn(content, saved)
        self.assertEqual(len(self.memory.history()), 4)
        self.assertTrue(looks_like_command("Pode fazer"))

    def test_other_turn_invalidates_stale_permission(self):
        yuna.handle_message(self.memory, "O que você quer fazer?")
        with patch("yuna.respond", return_value="Claro, posso explicar."):
            yuna.handle_message(self.memory, "O que significa Python?")
        self.assertIsNone(pending_own_activity(self.memory.initiative))
        self.assertFalse(is_authorization("Como você pode fazer isso?"))
        self.assertFalse(is_authorization("Não pode fazer"))
        self.assertFalse((self.memory.folder / "diario_yuna.md").exists())

    def test_rejection_discards_proposal_without_writing(self):
        yuna.handle_message(self.memory, "O que você quer fazer?")
        answer = yuna.handle_message(self.memory, "Agora não")
        self.assertIn("outra hora", answer)
        self.assertIsNone(pending_own_activity(self.memory.initiative))
        self.assertFalse((self.memory.folder / "diario_yuna.md").exists())

    def test_next_idea_is_self_contained_and_not_system_changes(self):
        yuna.handle_message(self.memory, "O que você quer fazer?")
        next_idea = yuna.handle_message(self.memory, "Yuna, o que você quer fazer?")
        self.assertIn("Quero pensar em uma melhoria", next_idea)
        answer = yuna.handle_message(self.memory, "Pode fazer")
        self.assertIn("Minha proposta", answer)
        self.assertIn("Não alterei nenhum código", answer)
        self.assertFalse((self.memory.folder / "diario_yuna.md").exists())
        self.assertIsNone(pending_own_activity(self.memory.initiative))

    def test_proposal_rotation_survives_restart(self):
        first = propose_own_activity(self.memory.initiative)
        self.assertIn("diário", first)
        self.memory.close()
        self.memory = yuna.Memory(Path(self.temp.name) / "data" / "yuna.db")
        second = propose_own_activity(self.memory.initiative)
        self.assertIn("melhoria", second)

    def test_failed_diary_keeps_proposal_no_false_success(self):
        yuna.handle_message(self.memory, "O que você quer fazer?")
        with patch("yuna.generate_entry", side_effect=RuntimeError("Ollama não respondeu")):
            with self.assertRaisesRegex(RuntimeError, "Ollama"):
                yuna.handle_message(self.memory, "Pode fazer")
        self.assertIsNotNone(pending_own_activity(self.memory.initiative))
        self.assertFalse((self.memory.folder / "diario_yuna.md").exists())


if __name__ == "__main__":
    unittest.main()
