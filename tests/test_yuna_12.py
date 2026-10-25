"""Verifica ações com navegador e pesquisa pública sem usar internet nos testes."""
import io
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import unittest

from web_actions import handle_web_command, wikipedia_lookup, open_allowed_url, public_question_to_query
from screen_consent import ScreenConsent
from yuna import startup_greeting, identity_reply
from datetime import datetime, timezone


class BrowserTests(unittest.TestCase):
    def test_open_and_search_youtube(self):
        with patch("web_actions.open_allowed_url", return_value="Abri YouTube") as opener:
            self.assertEqual(handle_web_command("Yuna, abre Chrome e abre o YouTube"), "Abri YouTube")
            opener.assert_called_once_with("https://www.youtube.com", chrome=True)
        with patch("web_actions.open_allowed_url", return_value="Pesquisei") as opener:
            self.assertEqual(handle_web_command("Pesquise música clássica no YouTube"), "Pesquisei")
            self.assertIn("search_query=musica%20classica", opener.call_args.args[0])

    def test_reuse_chrome_for_next_youtube_search(self):
        class Session:
            prefer_chrome = False
        session = Session()
        with patch("web_actions.open_allowed_url", return_value="Ok") as opened:
            handle_web_command("Abra Chrome e abre YouTube", session)
            handle_web_command("Pesquisa astronomia no YouTube", session)
            self.assertTrue(session.prefer_chrome)
            self.assertTrue(opened.call_args.kwargs["chrome"])

    def test_auto_lookup_only_public_general_questions(self):
        self.assertEqual(public_question_to_query("O que é energia escura?"), "energia escura")
        self.assertIsNone(public_question_to_query("Quem é meu pai?"))
        self.assertIsNone(public_question_to_query("Como está minha conta?"))

    def test_no_actions_for_questions_or_negations(self):
        with patch("web_actions.open_allowed_url") as opener:
            self.assertIsNone(handle_web_command("Como faço para abrir o YouTube?"))
            self.assertIsNone(handle_web_command("Não abra YouTube"))
            opener.assert_not_called()

    def test_media_key_uses_bounded_action(self):
        with patch("web_actions.media_key", return_value="Enviei pausa") as player:
            self.assertEqual(handle_web_command("pausa"), "Enviei pausa")
            player.assert_called_once_with("pause")
        with self.assertRaisesRegex(ValueError, "Só abro"):
            open_allowed_url("https://example.com/meu-site")

    def test_wikipedia_search_has_source_and_does_not_leak(self):
        response = {"pages": [{
            "title": "Astronomia", "description": "Estudo dos astros",
            "excerpt": "Estudo do <span class='searchmatch'>Universo</span>",
            "key": "Astronomia",
        }]}
        value = io.BytesIO(json.dumps(response).encode("utf-8"))
        with patch("web_actions.urllib.request.urlopen", return_value=value) as opener:
            result = wikipedia_lookup("astronomia")
        self.assertIn("https://pt.wikipedia.org/wiki/Astronomia", result)
        self.assertIn("Universo", result)
        self.assertIn("q=astronomia", opener.call_args.args[0].full_url)
        with patch("web_actions.urllib.request.urlopen") as private:
            self.assertIn("privados", wikipedia_lookup("minha senha secreta"))
            private.assert_not_called()


class IdentityAndScreenTests(unittest.TestCase):
    def test_time_based_greetings(self):
        self.assertIn("bom dia", startup_greeting(datetime(2026, 10, 25, 9, 12, tzinfo=timezone.utc)).lower())
        self.assertIn("boa noite", startup_greeting(datetime(2026, 10, 25, 20, 12, tzinfo=timezone.utc)).lower())

    def test_creator_identity(self):
        self.assertIn("Kaizen", identity_reply(None, "quem criou você?"))
        self.assertIn("pai", identity_reply(None, "quem é seu pai?"))

    def test_screen_auto_observe_requires_local_opt_in(self):
        with tempfile.TemporaryDirectory() as directory:
            consent = ScreenConsent(directory)
            self.assertFalse(consent.enabled)
            consent.set_enabled(True)
            self.assertTrue(ScreenConsent(directory).enabled)
            consent.set_enabled(False)
            self.assertFalse(consent.enabled)

    def test_gui_uses_scrollable_copyable_text(self):
        ui = (Path(__file__).parents[1] / "yuna_overlay.py").read_text(encoding="utf-8")
        self.assertIn("self.bubble = QTextEdit()", ui)
        self.assertIn("self.bubble.setReadOnly(True)", ui)
        self.assertIn("self.bubble.setVerticalScrollBarPolicy(", ui)
        self.assertIn("QApplication.clipboard().setText(text)", ui)
        self.assertIn("self.screen_confirm_pending", ui)
        self.assertIn("self.dialogue.request_screen()", ui)


if __name__ == "__main__":
    unittest.main()
