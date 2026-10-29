"""Integração da preferência de voz no desktop; sem hardware real."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@unittest.skipUnless(importlib.util.find_spec("PySide6"), "Qt opcional")
class PersonaDesktopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_natural_request_is_saved_without_using_ollama(self):
        from yuna_desktop import YunaDesktop
        from persona_store import load_preferences
        with tempfile.TemporaryDirectory() as folder, patch(
                "yuna_desktop.ROOT", Path(folder)), patch(
                "yuna_desktop.DesktopWorker.start"):
            window = YunaDesktop()
            try:
                with patch.object(window, "say") as say:
                    window.composer.setPlainText("Yuna, quero que vire homem")
                    window.send_message()
                self.assertEqual(window.persona.presentation, "masculina")
                self.assertEqual(window.presentation_selector.currentIndex(), 1)
                self.assertEqual(load_preferences(folder).presentation, "masculina")
                say.assert_called_once()
            finally:
                window.close()

    def test_tts_receives_gender_and_style(self):
        from yuna_desktop import YunaDesktop
        with tempfile.TemporaryDirectory() as folder, patch(
                "yuna_desktop.ROOT", Path(folder)), patch(
                "yuna_desktop.DesktopWorker.start"):
            window = YunaDesktop()
            try:
                window.persona = window.persona.updated(
                    presentation="masculina", voice_style="suave")
                with patch("yuna_desktop.Thread") as mock_thread, patch(
                        "yuna_desktop.synthesize_windows", return_value=None) as synthesis:
                    window.say("Teste")
                    callback = mock_thread.call_args.kwargs["target"]
                    callback()
                    synthesis.assert_called_once_with(
                        "Teste", "masculina", "suave")
            finally:
                window.close()
