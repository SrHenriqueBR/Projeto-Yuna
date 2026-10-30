"""Contratos fixos, sem modelo, rede, Qt ou dados pessoais.

Copiados sem alterações para o laboratório; os testes gerados são adicionais.
"""
import unittest
from language_quality import has_language_problem, identity_conversation_reply, normalized
from natural_interaction import classify_public_request


class LanguageContract(unittest.TestCase):
    def test_invalid_grammar(self):
        for text in ("Vou pode ajudar.", "Sou chama de Yuna.", "Estou animado.",
                     "Eu não tenho um nome próprio.", "Seu nome é Yuna."):
            with self.subTest(text=text):
                self.assertTrue(has_language_problem(text))

    def test_valid_text_and_quotations(self):
        for text in ("Estou pronta para ajudar.", "Obrigada pela conversa!",
                     'Ela escreveu: “Vou pode ajudar”.', 'Exemplo: `vou pode`',
                     '> Eu sou Kaizen\nEstou pronta.'):
            with self.subTest(text=text):
                self.assertFalse(has_language_problem(text))

    def test_empty_answer_is_invalid(self):
        self.assertTrue(has_language_problem(""))
        self.assertTrue(has_language_problem(None))

    def test_normalization(self):
        self.assertEqual(normalized("Olá, Yuna! Tudo BOM?"), "tudo bom")

    def test_identity_and_unrelated_context(self):
        self.assertIn("Yuna", identity_conversation_reply("Qual seu nome?"))
        self.assertIsNone(identity_conversation_reply("E o seu?", []))
        self.assertIsNone(identity_conversation_reply("Vamos falar sobre programação"))


class IntentContract(unittest.TestCase):
    def test_weather(self):
        intent = classify_public_request("Yuna, como está o tempo em Uberlândia?")
        self.assertEqual((intent.operation, intent.argument), ("weather", "uberlandia"))

    def test_books(self):
        intent = classify_public_request("Procure livros sobre Python")
        self.assertEqual((intent.operation, intent.argument), ("books", "python"))

    def test_explicit_external_provider(self):
        intent = classify_public_request("Pergunte ao Gemini o que é programação")
        self.assertEqual((intent.operation, intent.provider), ("external_ai", "gemini"))

    def test_negation_hypotheses_and_conversation(self):
        for text in ("Não procure livros sobre Python", "Nunca consulte o CEP 01310930",
                     "Se eu perguntar ao Gemini, ele responde?", "Eu gosto de livros sobre Python",
                     "O que é o Gemini?", "Como posso pesquisar livros sobre Python?",
                     "Talvez eu pesquise o clima amanhã", "/livros Python"):
            with self.subTest(text=text):
                self.assertIsNone(classify_public_request(text))


if __name__ == "__main__":
    unittest.main()
