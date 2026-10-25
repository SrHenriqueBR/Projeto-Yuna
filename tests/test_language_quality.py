"""Regression tests for Brazilian Portuguese and Yuna's stable identity."""
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from language_quality import has_language_problem, identity_conversation_reply, normalized
import yuna


class PortugueseQualityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.memory = yuna.Memory(Path(self.temp.name) / "yuna.db")

    def tearDown(self):
        self.memory.close()
        self.temp.cleanup()

    def test_detects_actual_screenshot_errors(self):
        for utterance in [
            "Vou pode falar sobre o seu livro.",
            "Vou precisa de abrir o Word primeiro.",
            "Sou chama de Yuna quando sou eu.",
            "Sou muito especial ter essa conexão com você.",
            "Eu não tenho um nome próprio.",
            "Estou animado de estar aqui.",
        ]:
            with self.subTest(utterance):
                self.assertTrue(has_language_problem(utterance), utterance)
                self.assertTrue(yuna.speech_issue(utterance), utterance)

    def test_does_not_flag_valid_language_or_quoted_text(self):
        for utterance in [
            "Oi, Kaizen! Meu nome é Yuna, e estou pronta para ajudar.",
            "Você é meu criador no Projeto Yuna.",
            "A personagem escreveu: “Não tenho nome próprio”.",
        ]:
            with self.subTest(utterance):
                self.assertFalse(has_language_problem(utterance), utterance)

    def test_normalizes_salutation_without_changing_name(self):
        self.assertEqual(normalized("Olá Yuna, tudo bom?"), "tudo bom")
        self.assertEqual(normalized("Isso, e o seu?"), "isso e o seu")

    def test_identity_replies_are_clear_and_correct(self):
        self.assertIn("Tudo bem", identity_conversation_reply("Olá yuna tudo bom?"))
        self.assertIn("Yuna", identity_conversation_reply(
            "Isso, e o seu?",
            [{"role": "user", "content": "Sabe meu nome?"},
             {"role": "assistant", "content": "Seu nome é Kaizen."}],
        ))
        self.assertIsNone(identity_conversation_reply("E o seu?", []))
        self.assertIn("Kaizen", identity_conversation_reply(
            "Você é a Yuna, você é a Yuna, minha criação meu tesouro"
        ))

    def test_dialogue_bypasses_model_for_identity_context(self):
        self.memory.save_turn("Sabe meu nome?", "Seu nome é Kaizen.")
        with patch("yuna.respond", side_effect=AssertionError("Do not call model")):
            result = yuna.handle_message(self.memory, "Isso, e o seu?", None)
        self.assertIn("Meu nome é Yuna", result)

    def test_bad_history_is_not_fed_back_to_model(self):
        self.memory.save_turn("Qual seu nome?", "Sou chama de Yuna quando sou eu.")
        self.memory.save_turn("Vamos conversar", "Claro, Kaizen. O que gostaria de fazer?")
        contents = [x["content"] for x in yuna.conversation_history(self.memory)]
        self.assertNotIn("Sou chama de Yuna quando sou eu.", contents)
        self.assertIn("Claro, Kaizen. O que gostaria de fazer?", contents)

    def test_model_command_is_local(self):
        with patch("yuna.ask_model", side_effect=AssertionError("No model call")):
            self.assertIn(yuna.MODEL, yuna.handle_message(self.memory, "/modelo"))

    def test_quality_revision_keeps_usable_response(self):
        outputs = iter([
            "Sou chama de Yuna quando sou eu.",
            "Meu nome é Yuna, Kaizen. Sou sua assistente pessoal.",
        ])
        with patch("yuna.ask_model", side_effect=lambda *args, **kwargs: next(outputs)):
            answer = yuna.respond(self.memory, "Qual o seu nome?")
        self.assertEqual(answer, "Meu nome é Yuna, Kaizen. Sou sua assistente pessoal.")


if __name__ == "__main__":
    unittest.main()
