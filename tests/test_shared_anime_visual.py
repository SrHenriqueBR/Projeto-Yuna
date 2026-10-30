"""Identidade visual compartilhada entre demo web e desktop.

Não abre rede, não requer navegador e não expõe dados pessoais.
"""
from pathlib import Path
import importlib.util
import os
from unittest.mock import patch
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SharedVisualTests(unittest.TestCase):
    def test_same_image_is_used_by_web_and_desktop(self):
        portrait = ROOT / "docs" / "yuna-portrait.webp"
        data = portrait.read_bytes()
        self.assertTrue(data.startswith(b"RIFF"))
        self.assertEqual(data[8:12], b"WEBP")
        self.assertLess(len(data), 100_000)
        page = (ROOT / "docs" / "yuna-preview.html").read_text(encoding="utf-8")
        desktop = (ROOT / "yuna_desktop.py").read_text(encoding="utf-8")
        self.assertIn('src="./yuna-portrait.webp"', page)
        self.assertIn('"yuna-portrait.webp"', desktop)
        self.assertIn("select_hero_mood", desktop)
        self.assertIn('class="poster"', page)
        self.assertIn('id="portrait"', page)

    def test_web_page_has_local_only_visual_preview(self):
        html = (ROOT / "docs" / "yuna-preview.html").read_text(encoding="utf-8")
        for mood in ("idle", "happy", "shy", "angry", "wave", "sleep"):
            self.assertIn('data-action="' + mood + '"', html)
        self.assertNotIn("getUserMedia(", html)
        self.assertNotIn("https://api.openai.com", html)


@unittest.skipUnless(importlib.util.find_spec("PySide6"), "Qt não instalado")
class SharedVisualQtTests(unittest.TestCase):
    def test_anime_panel_does_not_block_chat_or_start_services(self):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        from PySide6.QtWidgets import QApplication
        from yuna_desktop import YunaDesktop

        app = QApplication.instance() or QApplication([])
        with patch("yuna_desktop.DesktopWorker.start"):
            window = YunaDesktop()
        try:
            window.show()
            app.processEvents()
            self.assertIsNotNone(window.hero_image)
            self.assertIsNotNone(window.hero_speech)
            self.assertIsNone(window.avatar_bridge)
            self.assertEqual(len(window.hero_buttons), 6)
            window.select_hero_mood("happy")
            self.assertIn("feliz", window.hero_speech.text().lower())
            self.assertTrue(window.send_button.isEnabled())
            self.assertIsNone(window.camera_viewer)
            self.assertIsNone(window.home_safety_dialog)
        finally:
            window.close()
            app.processEvents()


if __name__ == "__main__":
    unittest.main()
