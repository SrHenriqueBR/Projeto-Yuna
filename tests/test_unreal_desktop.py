"""Qt smoke da integração Unreal; nunca abre o editor ou uma porta de rede."""
import importlib.util
import os
from unittest.mock import patch
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
QT = importlib.util.find_spec("PySide6") is not None


@unittest.skipUnless(QT, "PySide6 opcional")
class UnrealDesktopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def make_window(self):
        from yuna_desktop import YunaDesktop
        with patch("yuna_desktop.DesktopWorker.start"):
            return YunaDesktop()

    def test_opt_in_and_voice_events_without_starting_unreal(self):
        window = self.make_window()
        try:
            self.assertIsNone(window.unreal_bridge)
            self.assertFalse(window.unreal_button.text().startswith("■"))
            with patch("yuna_desktop.QDesktopServices.openUrl", return_value=True):
                window.toggle_unreal_bridge()
            self.assertIsNotNone(window.unreal_bridge)
            self.assertTrue(window.unreal_bridge.path.exists())
            self.assertIsNone(window.avatar_bridge)
            window._avatar_event("avatar.pose", pose="wave")
            import json
            state = json.loads(window.unreal_bridge.path.read_text(encoding="utf-8"))
            self.assertEqual(state["pose"], "wave")
            window._avatar_event("speech.started", speech_id="s123")
            window._avatar_event("speech.level", speech_id="s123",
                                 amplitude=0.5, position_ms=120)
            state = json.loads(window.unreal_bridge.path.read_text(encoding="utf-8"))
            self.assertTrue(state["speaking"])
            window._avatar_event("speech.interrupted", speech_id="s123")
            state = json.loads(window.unreal_bridge.path.read_text(encoding="utf-8"))
            self.assertFalse(state["speaking"])
            self.assertEqual(state["mouth_level"], 0)
            window.toggle_unreal_bridge()
            self.assertIsNone(window.unreal_bridge)
        finally:
            window.close()

    def test_close_removes_session_state(self):
        window = self.make_window()
        with patch("yuna_desktop.QDesktopServices.openUrl", return_value=True):
            window.toggle_unreal_bridge()
        path = window.unreal_bridge.path
        self.assertTrue(path.is_file())
        window.close()
        self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
