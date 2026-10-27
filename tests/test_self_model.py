"""Yuna 0.10: identidade fiel e planejamento apenas consultivo."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import self_model
import yuna


class SelfModelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "yuna.db"
        self.memory = yuna.Memory(self.path)

    def tearDown(self):
        self.memory.close()
        self.temp.cleanup()

    def example(self, observacao="Você pretende melhorar o projeto.",
                proximo_passo="Liste uma melhoria pequena e teste.",
                duvida="Qual módulo vem primeiro?"):
        return json.dumps({
            "observacao": observacao,
            "proximo_passo": proximo_passo,
            "duvida": duvida
        })

    def test_about_is_verified_without_model_or_actions(self):
        with patch("yuna.ask_model", side_effect=AssertionError("Não deve usar modelo")):
            result = yuna.handle_message(self.memory, "como esta seu codigo", Mock())
        self.assertIn("Yuna 0.16", result)
        self.assertIn("Ollama", result)
        self.assertIn("não", result.lower())
        self.assertIn("memória", result.lower())
        self.assertTrue(self_model.is_self_question("Yuna, como está seu código?"))
        self.assertTrue(self_model.is_self_question(
            "Bom, primeiro quero saber como está o seu código"))
        self.assertFalse(self_model.is_self_question("Não quero saber como está seu código"))
        self.assertEqual(self.memory.history()[-1]["role"], "assistant")

    def test_natural_conversation_not_routed_to_actions(self):
        self.assertFalse(yuna.action_intent("Bom, quero saber como está seu código"))
        self.assertFalse(yuna.action_intent("Pode executar o que quiser no meu PC"))
        self.assertFalse(yuna.action_intent("Como posso abrir a Steam?"))
        self.assertTrue(yuna.action_intent("Quero ver os programas instalados"))
        self.assertTrue(yuna.action_intent("/fazer coloca o Discord pra rodar"))
        computer = Mock()
        computer.handle.return_value = None
        with patch("yuna.respond", return_value="Podemos conversar sobre isso.") as chat, \
                patch("yuna.interpret", side_effect=AssertionError("Não deve interpretar ações")):
            self.assertEqual(
                yuna.handle_message(self.memory, "Quero conversar sobre meu projeto", computer),
                "Podemos conversar sobre isso.")
            chat.assert_called_once()

    def test_planning_store_and_restart(self):
        ask = Mock(return_value=self.example())
        result = self.memory.thinking.plan("melhorar projeto Yuna", ask)
        self.assertIn("O que percebi", result)
        self.assertEqual(ask.call_args.kwargs["schema"], self_model.THINK_SCHEMA)
        self.assertEqual(len(self.memory.thinking.recent()), 1)
        self.memory.close()
        self.memory = yuna.Memory(self.path)
        self.assertEqual(self.memory.thinking.recent()[0][2],
                         "Liste uma melhoria pequena e teste.")
        self.assertEqual(self.memory.thinking.forget(self.memory.thinking.recent()[0][0]), 1)
        self.assertEqual(self.memory.thinking.recent(), [])

    def test_reject_invalid_or_sensitive_thoughts(self):
        for output in ["nao json", '{"observacao": "Apenas uma chave"}',
                       self.example(proximo_passo=""),
                       self.example(observacao="Minha senha é abc123"),
                       self.example(proximo_passo="x" * 181)]:
            with self.assertRaises(ValueError):
                self.memory.thinking.plan("aprimorar projeto", Mock(return_value=output))
        reply = self.memory.thinking.plan("Minha senha é 123456", Mock())
        self.assertIn("confidenciais", reply)
        self.assertEqual(self.memory.thinking.recent(), [])

    def test_periodic_review_every_six_eligible_turns(self):
        ask = Mock(return_value=self.example())
        for index in range(5):
            self.assertIsNone(self.memory.thinking.maybe_reflect(
                f"Hoje quero avançar no projeto número {index}", ask))
        ask.assert_not_called()
        self.assertIsNone(self.memory.thinking.maybe_reflect(
            "Como funciona sua arquitetura?", ask))
        self.assertIsNone(self.memory.thinking.maybe_reflect(
            "Minha senha é abc123", ask))
        result = self.memory.thinking.maybe_reflect(
            "Hoje vou terminar o projeto da Yuna", ask)
        self.assertIn("O que percebi", result)
        ask.assert_called_once()
        self.assertEqual(len(self.memory.thinking.recent()), 1)
        self.memory.thinking.enable(False)
        ask.reset_mock()
        for i in range(20):
            self.memory.thinking.maybe_reflect("Vou aprender a programar melhor", ask)
        ask.assert_not_called()

    def test_clear_semantics(self):
        ask = Mock(return_value=self.example())
        self.memory.thinking.plan("o projeto", ask)
        self.memory.clear()
        self.assertEqual(len(self.memory.thinking.recent()), 1)
        self.memory.clear(all_data=True)
        self.assertEqual(self.memory.thinking.recent(), [])

    def test_plans_are_not_automated_commands(self):
        suggestion = "Abra o terminal e revise o código somente se quiser."
        self.memory.thinking.plan("revisar arquitetura", Mock(return_value=self.example(
            proximo_passo=suggestion)))
        self.assertIn(suggestion, self.memory.thinking.recent()[0])
        # Este módulo não importa subprocess, Desktop ou Computer para executar sugestões.
        self.assertFalse(hasattr(self_model, "subprocess"))
        self.assertFalse(hasattr(self_model, "Computer"))


if __name__ == "__main__":
    unittest.main()
