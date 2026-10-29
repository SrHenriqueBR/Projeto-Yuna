"""Botão Parar deve revogar qualquer sessão em memória."""
import importlib.util
import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

@unittest.skipUnless(importlib.util.find_spec("PySide6"), "Qt opcional")
class GameSessionQtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_global_stop_revokes_game_permission(self):
        from yuna_desktop import YunaDesktop
        with patch("yuna_desktop.DesktopWorker.start"):
            window = YunaDesktop()
        try:
            self.assertFalse(window.game_session.active)
            window.game_session.authorize(
                r"C:\Games\Demo\Game.exe",
                approved=True, single_player=True,
            )
            self.assertTrue(window.game_session.active)
            window.emergency_stop()
            self.assertFalse(window.game_session.active)
        finally:
            window.close()


if __name__ == "__main__":
    unittest.main()
