"""Qt offscreen smoke test to catch actual desktop GUI construction errors."""
import importlib.util
import os
from unittest.mock import patch
import unittest

QT = importlib.util.find_spec("PySide6") is not None


@unittest.skipUnless(QT, "PySide6 not installed")
class DesktopWindowSmokeTests(unittest.TestCase):
    def test_chat_window_builds_and_widgets_are_operational(self):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        from PySide6.QtWidgets import QApplication
        from yuna_desktop import YunaDesktop

        app = QApplication.instance() or QApplication([])
        with patch("yuna_desktop.DesktopWorker.start"):
            window = YunaDesktop()
            window.show()
            app.processEvents()
            try:
                self.assertIn("Yuna", window.windowTitle())
                self.assertTrue(window.send_button.isEnabled())
                self.assertEqual(window.voice_selector.count(), 3)
                self.assertIsNotNone(window.files_list)
                self.assertIsNotNone(window.microphone_button)
                self.assertIsNone(window.pending_path)
                window.add_message("Kaizen", "Oi Yuna!")
                window.add_message("Yuna", "Olá, Kaizen! 🖤")
                app.processEvents()
                self.assertGreater(window.message_column.count(), 2)
                window.composer.setPlainText("Pergunta longa" * 500)
                self.assertGreater(len(window.composer.toPlainText()), 5000)
            finally:
                window.close()
                app.processEvents()


if __name__ == "__main__":
    unittest.main()
