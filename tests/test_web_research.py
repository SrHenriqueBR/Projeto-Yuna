from io import BytesIO
import json
import unittest
from unittest.mock import patch

import web_actions as web
import yuna


class PublicResearchTests(unittest.TestCase):
    def setUp(self):
        web._CACHE.clear()

    def tearDown(self):
        web._CACHE.clear()

    def response(self):
        return BytesIO(json.dumps({"pages": [{"title": "Python", "key": "Python",
                                              "description": "Linguagem", "excerpt": "<b>Código</b> público"}]}).encode())

    def test_repeated_public_query_uses_short_cache_and_cites_source(self):
        with patch("web_actions.urllib.request.urlopen", return_value=self.response()) as request:
            first = web.wikipedia_lookup("Python")
            second = web.wikipedia_lookup("python")
        self.assertIn("Fonte: https://pt.wikipedia.org/wiki/Python", first)
        self.assertIn("Cache local", second)
        self.assertNotIn("<b>", first)
        request.assert_called_once()

    def test_cache_expires(self):
        with patch("web_actions.time.monotonic", return_value=10), patch("web_actions.urllib.request.urlopen", return_value=self.response()):
            web.wikipedia_lookup("Python")
        with patch("web_actions.time.monotonic", return_value=131), patch("web_actions.urllib.request.urlopen", return_value=self.response()) as call:
            self.assertNotIn("Cache local", web.wikipedia_lookup("Python"))
        call.assert_called_once()

    def test_private_queries_are_not_sent_or_cached(self):
        with patch("web_actions.urllib.request.urlopen") as network:
            for query in ("minha senha teste123", "CPF 123", "contato eu@example.com", r"C:\Users\Kaizen\segredo"):
                with self.subTest(query=query):
                    self.assertIn("privados", web.wikipedia_lookup(query))
            self.assertEqual(len(web._CACHE), 0)
        network.assert_not_called()

    def test_general_web_search_opens_only_explicit_query_and_does_not_claim_reading(self):
        with patch("web_actions.open_allowed_url", return_value="Solicitei abertura") as open_url:
            result = web.handle_web_command("Yuna, pesquise na web sobre atualizações do Windows")
        self.assertIn("não li", result)
        self.assertEqual(open_url.call_args.args[0], "https://www.google.com/search?q=atualizacoes+do+windows")
        with patch("web_actions.open_allowed_url") as open_url:
            self.assertIsNone(web.handle_web_command("Não pesquise na web gatos"))
        open_url.assert_not_called()

    def test_chat_router_respects_web_destination_instead_of_searching_wikipedia(self):
        with patch("web_actions.open_allowed_url", return_value="Solicitei abertura") as browser, \
                patch("yuna.wikipedia_lookup", side_effect=AssertionError("Wrong destination")), \
                patch("yuna.ask_model", side_effect=AssertionError("No model")):
            result = yuna.handle_message(None, "Yuna, pesquise na web sobre Python")
        browser.assert_called_once()
        self.assertIn("não li", result)

    def test_malformed_or_oversized_responses_do_not_enter_cache(self):
        for data in (b'[]', b'{"pages":[null,{"title":42}]}', b'a' * 256001):
            with self.subTest(size=len(data)), patch("web_actions.urllib.request.urlopen", return_value=BytesIO(data)):
                self.assertNotIn("Fonte:", web.wikipedia_lookup("Python"))
        self.assertFalse(web._CACHE)

    def test_empty_and_overlong_queries_remain_invalid(self):
        for query in ("", " " * 3, "a" * 161):
            with self.subTest(query=query), self.assertRaises(ValueError):
                web.wikipedia_lookup(query)


if __name__ == "__main__":
    unittest.main()
