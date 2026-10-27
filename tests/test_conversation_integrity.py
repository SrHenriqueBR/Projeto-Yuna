"""Regressões extraídas da conversa real de Kaizen com a Yuna."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import yuna
from conversation_integrity import grounded_reply, explicit_public_lookup


class ConversationIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.memory = yuna.Memory(Path(self.tmp.name) / "yuna.db")

    def tearDown(self):
        self.memory.close()
        self.tmp.cleanup()

    def test_future_shutdown_is_not_promised_or_scheduled(self):
        for phrase in [
            "Depois que der 00:00 pode desligar o computador?",
            "Yuna, desligue o PC quando for meia-noite",
        ]:
            with self.subTest(phrase):
                with patch("yuna.ask_model", side_effect=AssertionError("Ollama must not decide shutdown")):
                    output = yuna.handle_message(self.memory, phrase)
                self.assertIn("Não programei", output)
                self.assertIn("confirmação", output)

    def test_open_ended_web_permission_is_not_autonomous_browsing(self):
        with patch("yuna.ask_model", side_effect=AssertionError("Should be a grounded response")):
            response = yuna.handle_message(self.memory,
                "Quer ficar ativa para procurar algo na net?")
        self.assertIn("não fico navegando", response.lower())

    def test_user_allows_code_updates_but_yuna_is_review_only(self):
        message = "Yuna, você pode modificar seu código a qualquer momento"
        with patch("yuna.ask_model", side_effect=AssertionError("No model needed")):
            response = yuna.handle_message(self.memory, message)
        self.assertIn("não alterei nenhum arquivo", response.lower())
        self.assertIn("revisar", response)

    def test_friday_reference_is_understood_without_hallucination(self):
        response = yuna.handle_message(self.memory,
            "Quero que voce tenha mais conhecimento, como a Sexta Feira do Tony Stark")
        self.assertIn("FRIDAY", response)
        self.assertIn("Tony Stark", response)
        self.assertNotIn("difícil encontrar", response)

    def test_god_of_war_question_does_not_claim_to_play(self):
        response = yuna.handle_message(self.memory, "Você quer jogar?")
        self.assertIn("God of War", response)
        self.assertIn("não consigo", response)
        self.assertNotIn("não tenho interesse", response)
        self.assertIsNone(yuna.public_question_to_query("Quem ele é?"))

    def test_kratos_is_only_claimed_researched_with_real_source(self):
        with patch("yuna.wikipedia_lookup", return_value=(
            "Kratos: Personagem de God of War.\n"
            "Fonte: https://pt.wikipedia.org/wiki/Kratos_(God_of_War)"
        )) as source, patch("yuna.ask_model", side_effect=AssertionError("No Ollama needed")):
            result = yuna.handle_message(self.memory, "Tente procurar sobre Kratos")
        source.assert_called_once_with("kratos")
        self.assertIn("Consultei a Wikipédia agora", result)
        self.assertIn("Fonte:", result)
        with patch("yuna.wikipedia_lookup", return_value="Serviço indisponível."):
            result = yuna.handle_message(self.memory, "Tente procurar sobre Kratos")
        self.assertIn("Não encontrei fontes verificáveis", result)

    def test_weather_without_city_requires_real_data(self):
        with patch("yuna.ask_model", side_effect=AssertionError("No made-up forecast")):
            reply = yuna.handle_message(self.memory, "Como está o clima hoje?")
        self.assertIn("qual cidade", reply.lower())
        self.assertNotIn("está bom", reply)

    def test_language_matches_real_errors(self):
        for phrase in [
            "Vou gostaria de jogar",
            "Estou tão bom, Kaizen",
            "Como estou hoje?",
            "Estou se sentindo sozinho",
            "Vou ter alguma tarefa em particular",
        ]:
            with self.subTest(phrase):
                self.assertTrue(yuna.speech_issue(phrase), phrase)

    def test_failed_rewrite_does_not_ask_to_rephrase_intimate_explanation(self):
        statement = ("Quero que você tenha mais conhecimento e iniciativa "
                     "para ser uma assistente mais útil no meu computador.")
        with patch("yuna.public_question_to_query", return_value=None):
            with patch("yuna.ask_model", side_effect=[
                "Vou gostaria de te ajudar", "Sou Kaizen!"]) as model:
                answer = yuna.respond(self.memory, statement)
        self.assertEqual(model.call_count, 2)
        self.assertIn("mais curiosa", answer)
        self.assertNotIn("reformular", answer.lower())

    def test_no_background_actions_after_goodnight(self):
        with patch("yuna.ask_model", side_effect=AssertionError("Should not run task")):
            output = yuna.handle_message(self.memory,
                "Depois que der 00:00 pode desligar o computador?")
        self.assertIn("Não programei", output)


if __name__ == "__main__":
    unittest.main()
