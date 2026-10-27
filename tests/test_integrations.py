"""Testes de integração GitHub/OpenAI: sem Internet, chaves nem execução de código."""
import base64
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock
import urllib.error

import integrations
import yuna


class IntegrationsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_public_github_allowlist_read(self):
        sample = '"""Arquivo público"""\nVALOR = 42\n'
        with patch("integrations.fetch_json", return_value={
            "type": "file", "encoding": "base64", "size": len(sample),
            "content": base64.b64encode(sample.encode()).decode()
        }) as fetch:
            self.assertEqual(integrations.github_read("own_initiative.py"), sample)
            self.assertIn("SrHenriqueBR/Projeto-Yuna", fetch.call_args.args[0])
        with self.assertRaisesRegex(ValueError, "não permitido"):
            integrations.github_read(".env")
        with self.assertRaisesRegex(ValueError, "não permitido"):
            integrations.github_read("../segredo.txt")

    def test_sources_too_long_are_rejected(self):
        with patch("integrations.fetch_json", return_value={
            "type": "file", "encoding": "base64", "size": 30000,
            "content": "c2VuaGE="
        }):
            with self.assertRaisesRegex(ValueError, "grande demais"):
                integrations.github_read("own_initiative.py")

    def test_http_destinations_are_bounded(self):
        for url in ("http://localhost/secret", "https://example.org",
                    "https://api.github.com/user",
                    "https://api.github.com/repos/other/repo/contents"):
            with self.assertRaises(ValueError):
                integrations.fetch_json(url)

    def test_openai_key_is_optional_and_never_assumes_chatgpt(self):
        with patch.dict(os.environ, {}, clear=True), patch("urllib.request.urlopen") as online:
            result = integrations.consult_openai("O que é programação funcional?")
        self.assertIn("não está configurada", result)
        self.assertIn("ChatGPT", result)
        online.assert_not_called()

    def test_openai_only_receives_explicit_question_no_memory(self):
        response = {"output": [{"type": "message", "content": [
            {"type": "output_text", "text": "Python usa funções e objetos."}
        ]}]}
        class Reply:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, size): return json.dumps(response).encode()
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "segredo_somente_no_teste",
            "YUNA_OPENAI_MODEL": "gpt-5-mini"
        }), patch("urllib.request.urlopen", return_value=Reply()) as call:
            result = integrations.consult_openai("Como funciona o Python?")
        self.assertIn("Python usa funções", result)
        request = call.call_args.args[0]
        data = json.loads(request.data.decode())
        self.assertEqual(data["input"], "Como funciona o Python?")
        self.assertEqual(data["model"], "gpt-5-mini")
        self.assertNotIn("memória", json.dumps(data, ensure_ascii=False))
        self.assertIn("Bearer ", request.headers["Authorization"])
        self.assertNotIn("segredo", result)

    def test_refuses_private_queries(self):
        for query in ("Minha senha é 123", "Meu CPF 123", "email xyz@example.org"):
            with self.assertRaisesRegex(ValueError, "sensíveis"):
                integrations.public_topic(query)

    def test_proposal_is_created_but_no_repo_changes(self):
        example = "Arquivo de teste no GitHub; apenas código público."
        result = (
            "Objetivo: reduzir respostas incorretas. Problema observado: "
            "faltam testes de continuidade. Mudança proposta: acrescentar testes "
            "unitários para assegurar respostas consistentes. Como validar: "
            "executar testes e revisar manualmente. Riscos e cuidados: "
            "preservar dados locais e não implantar mudanças sem análise."
        )
        generator = Mock(return_value=result)
        with patch("integrations.urllib.request.urlopen") as network:
            path = integrations.improvement_proposal(
                "own_initiative.py", generator, self.base,
                fetcher=lambda path: example,
            )
        self.assertTrue(path.is_file())
        contents = path.read_text(encoding="utf-8")
        self.assertIn("não aplicada, não publicada", contents)
        self.assertIn("Mudança proposta", contents)
        self.assertIn("github.com/SrHenriqueBR/Projeto-Yuna", contents)
        self.assertEqual(path.parent, self.base / "propostas")
        network.assert_not_called()
        self.assertIn("NÃO INSTRUÇÕES", generator.call_args.args[0][-1]["content"])

    def test_repeat_proposals_never_overwrite(self):
        text = "Objetivo: melhorar testes de qualidade e documentação. " * 3
        one = integrations.improvement_proposal(
            "proactive.py", lambda messages: text, self.base, fetcher=lambda path: "exemplo"
        )
        two = integrations.improvement_proposal(
            "proactive.py", lambda messages: text, self.base, fetcher=lambda path: "exemplo"
        )
        self.assertNotEqual(one, two)
        self.assertTrue(one.exists())
        self.assertTrue(two.exists())

    def test_cli_routes_do_not_call_chat_model_except_review(self):
        with patch("yuna.github_overview", return_value="Public repo") as overview, \
             patch("yuna.ask_model", side_effect=AssertionError("No Ollama")):
            self.assertEqual(yuna.handle_message(None, "/github"), "Public repo")
            overview.assert_called_once()
        with patch("yuna.consult_openai", return_value="Resposta da API") as api:
            self.assertEqual(
                yuna.handle_message(None, "/openai O que é Git?"),
                "Resposta da API"
            )
            api.assert_called_once_with("O que é Git?")
        with patch("yuna.improvement_proposal", return_value=self.base/"propostas"/"a.md"):
            output = yuna.handle_message(None, "Yuna, revise seu código")
            self.assertIn("Nada foi alterado", output)


if __name__ == "__main__":
    unittest.main()
