"""A Central lista Qwen3.5 local, preserva permissões e só instala após confirmar."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
QT = importlib.util.find_spec("PySide6") is not None


@unittest.skipUnless(QT, "PySide6 não disponível")
class QwenCenterQtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_ollama_model_buttons_are_explicit_and_non_paid(self):
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QCheckBox, QPushButton, QScrollArea, QWidget
        from app_center import YunaCenter

        class DummyWindow(QWidget):
            def toggle_avatar(self):
                pass
            def open_camera_viewer(self):
                pass
            def emergency_stop(self):
                pass

        class DummyController:
            window = DummyWindow()
            wake_action = QCheckBox()
            plug_action = QCheckBox()
            plug_voice = QCheckBox()
            show_compact = staticmethod(lambda: None)
            show_full = staticmethod(lambda: None)
            configure_game = staticmethod(lambda: None)
            tray_available = False

        with tempfile.TemporaryDirectory() as root:
            dialog = YunaCenter(DummyController(), Path(root))
            try:
                buttons = [b.text() for b in dialog.findChildren(QPushButton)]
                self.assertTrue(any("qwen3.5:2b" in b for b in buttons))
                self.assertTrue(any("qwen3.5:4b" in b for b in buttons))
                self.assertTrue(any("qwen3.5:9b" in b for b in buttons))
                self.assertTrue(any("Anterior padrão" in b for b in buttons))
                self.assertTrue(dialog.findChildren(QScrollArea))
                self.assertTrue("qwen2.5:3b" in dialog.current_model_label.text())
                with patch("app_center.QMessageBox.question",
                           return_value=0):
                    dialog.download_model("qwen3.5:4b")
                    self.assertFalse(dialog.running)
                self.assertFalse((Path(root) / "data/modelo_yuna.txt").exists())
            finally:
                dialog.sync.stop()
                dialog.deleteLater()


if __name__ == "__main__":
    unittest.main()
