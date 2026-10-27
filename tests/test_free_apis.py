"""Integrações do hub de APIs: testes inteiramente locais, sem rede nem chaves reais."""
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import free_apis
import yuna


class HubTests(unittest.TestCase):
    def test_public_weather_from_two_mocked_apis(self):
        calls = []
        def fake(url, **kwargs):
            calls.append(url)
            if "geocoding" in url:
                return {"results": [{"name": "Uberlândia", "admin1": "Minas Gerais",
                                     "country": "Brasil", "latitude": -18.91,
                                     "longitude": -48.28}]}
            return {"current": {"temperature_2m": 25.5,
                                "apparent_temperature": 27.2,
                                "relative_humidity_2m": 58,
                                "time": "2026-10-26T17:15"}}
        with patch("free_apis._json_request", side_effect=fake):
            result = yuna.handle_message(None, "/clima Uberlândia")
            natural = yuna.handle_message(None, "Yuna, qual é o clima em Uberlândia?")
        self.assertIn("25.5 °C", result)
        self.assertIn("Minas Gerais", natural)
        self.assertEqual(len(calls), 4)
        self.assertIn("latitude=", calls[1])
        self.assertIn("timezone=auto", calls[1])

    def test_no_private_or_ambiguous_city(self):
        with patch("free_apis._json_request") as remote:
            with self.assertRaisesRegex(ValueError, "dados pessoais"):
                free_apis.weather("minha senha")
            remote.assert_not_called()

    def test_books_returns_sources_from_search_api(self):
        with patch("free_apis._json_request", return_value={
            "docs": [{"title": "O Hobbit", "author_name": ["J. R. R. Tolkien"],
                      "first_publish_year": 1937, "key": "/works/OL262758W"}]
        }) as search:
            output = yuna.handle_message(None, "/livros fantasia")
        self.assertIn("O Hobbit", output)
        self.assertIn("Tolkien", output)
        self.assertIn("https://openlibrary.org/works/OL262758W", output)
        self.assertIn("limit=5", search.call_args.args[0])

    def test_postcode_explicit_query_validation(self):
        with patch("free_apis._json_request", return_value={
            "cep": "01310930", "state": "SP", "city": "São Paulo",
            "neighborhood": "Bela Vista", "street": "Avenida Paulista"
        }) as api:
            result = yuna.handle_message(None, "/cep 01310-930")
        self.assertIn("São Paulo", result)
        self.assertIn("CEP foi enviado", result)
        self.assertIn("/api/cep/v2/01310930", api.call_args.args[0])
        with patch("free_apis._json_request") as remote:
            with self.assertRaises(ValueError):
                free_apis.cep_lookup("invalid")
            remote.assert_not_called()

    def test_no_api_call_for_hypothetical_or_negated_text(self):
        with patch("free_apis._json_request") as request:
            self.assertIsNone(free_apis.handle_hub("Eu poderia pesquisar livros sobre Python?"))
            self.assertIsNone(free_apis.handle_hub("Não pesquise livros sobre Python"))
            self.assertIsNone(free_apis.handle_hub("Explique como funciona a API Gemini"))
            request.assert_not_called()

    def test_provider_status_never_discloses_keys(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "CHAVE_SECRETA_TESTE"}, clear=True):
            output = yuna.handle_message(None, "/ias")
        self.assertIn("gemini: chave configurada", output)
        self.assertIn("groq: sem chave", output)
        self.assertNotIn("CHAVE_SECRETA_TESTE", output)

    def test_no_model_call_without_key(self):
        with patch.dict(os.environ, {}, clear=True), patch("free_apis._json_request") as remote:
            output = yuna.handle_message(None, "/ia gemini Como melhorar um programa?")
        self.assertIn("GEMINI_API_KEY", output)
        remote.assert_not_called()

    def test_gemini_request_is_single_turn_public_text_only(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "DUMMYKEY"}, clear=True):
            with patch("free_apis._json_request", return_value={
                "candidates": [{"content": {"parts": [{"text": "Teste de resposta."}]}}]
            }) as call:
                result = yuna.handle_message(None, "/ia gemini O que é uma função Python?")
        self.assertIn("Teste de resposta", result)
        args = call.call_args
        self.assertIn("generateContent", args.args[0])
        self.assertEqual(args.kwargs["headers"]["x-goog-api-key"], "DUMMYKEY")
        body = args.kwargs["body"]
        self.assertEqual(len(body["contents"]), 1)
        self.assertIn("O que é uma função Python?", body["contents"][0]["parts"][0]["text"])

    def test_groq_and_openrouter_use_locked_models(self):
        for provider, env in (("groq", "GROQ_API_KEY"),
                              ("openrouter", "OPENROUTER_API_KEY")):
            with self.subTest(provider), patch.dict(os.environ, {env: "DUMMY"}, clear=True):
                with patch("free_apis._json_request", return_value={
                    "choices": [{"message": {"content": "Uma explicação."}}]
                }) as call:
                    answer = yuna.handle_message(None, f"/ia {provider} Explique sistemas operacionais")
                self.assertIn("Uma explicação", answer)
                self.assertEqual(call.call_args.kwargs["body"]["model"],
                                 free_apis.AI_MODELS[provider])
                self.assertEqual(len(call.call_args.kwargs["body"]["messages"]), 2)
                self.assertNotIn("memory", json.dumps(call.call_args.kwargs["body"]))

    def test_errors_do_not_expose_credentials(self):
        with patch.dict(os.environ, {"GROQ_API_KEY": "SECRET"}, clear=True):
            with patch("free_apis._json_request", side_effect=RuntimeError("Falha de rede")):
                with self.assertRaises(RuntimeError) as captured:
                    free_apis.ask_external_ai("groq", "Explique sistemas operacionais")
        self.assertNotIn("SECRET", str(captured.exception))

    def test_usage_no_automatic_paid_calls(self):
        with patch("free_apis._json_request") as network:
            output = yuna.handle_message(None, "/apis")
            self.assertIn("Open-Meteo", output)
            self.assertIn("Ollama", output)
            network.assert_not_called()

    def test_allowlist_does_not_accept_unrelated_urls(self):
        with self.assertRaisesRegex(ValueError, "não autorizado"):
            free_apis._json_request("http://127.0.0.1:9999/private")
        with self.assertRaisesRegex(ValueError, "não autorizado"):
            free_apis._json_request("https://openlibrary.org.evil.example/search.json")

    def test_gui_no_sensitive_api_readback_to_tts(self):
        content = (Path(__file__).parents[1] / "yuna_overlay.py").read_text(encoding="utf-8")
        self.assertIn('"/cep"', content)
        self.assertIn('"/ia "', content)


if __name__ == "__main__":
    unittest.main()
