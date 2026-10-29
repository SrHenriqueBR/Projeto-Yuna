"""Testes de consentimento da interface sem abrir a webcam nem instalar OpenCV."""
import importlib.util
import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@unittest.skipUnless(importlib.util.find_spec("PySide6"), "Qt opcional")
class CameraQtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def _desktop(self):
        from yuna_desktop import YunaDesktop
        with patch("yuna_desktop.DesktopWorker.start"):
            return YunaDesktop()

    def test_camera_starts_disabled_and_user_denial_does_nothing(self):
        from PySide6.QtWidgets import QMessageBox
        window = self._desktop()
        try:
            self.assertIsNone(window.camera_viewer)
            with patch("yuna_desktop.QInputDialog.getText", return_value=("0", True)), patch(
                    "yuna_desktop.QMessageBox.question",
                    return_value=QMessageBox.StandardButton.No), patch(
                    "yuna_desktop.CameraViewer") as viewer:
                window.open_camera_viewer()
                viewer.assert_not_called()
            self.assertIsNone(window.camera_viewer)
        finally:
            window.close()

    def test_approved_camera_is_opened_once_and_emergency_stop_closes(self):
        from PySide6.QtWidgets import QMessageBox
        window = self._desktop()
        try:
            with patch("yuna_desktop.QInputDialog.getText",
                       return_value=("webcam 0", True)), patch(
                       "yuna_desktop.QMessageBox.question",
                       return_value=QMessageBox.StandardButton.Yes), patch(
                       "yuna_desktop.CameraViewer.start_preview") as launch:
                window.open_camera_viewer()
                self.assertIsNotNone(window.camera_viewer)
                self.assertTrue(window.camera_viewer.isVisible())
                launch.assert_called_once()
                self.assertEqual(window.camera_viewer._permission.check().index, 0)
                window.emergency_stop()
                self.assertIsNone(window.camera_viewer)
        finally:
            window.close()

    def test_invalid_camera_is_rejected_before_consent(self):
        window = self._desktop()
        try:
            with patch("yuna_desktop.QInputDialog.getText",
                       return_value=("rtsp://8.8.8.8/live", True)), patch(
                       "yuna_desktop.QMessageBox.warning") as warning, patch(
                       "yuna_desktop.QMessageBox.question") as question:
                window.open_camera_viewer()
            warning.assert_called_once()
            question.assert_not_called()
            self.assertIsNone(window.camera_viewer)
        finally:
            window.close()

    def test_natural_command_never_bypasses_camera_picker(self):
        window = self._desktop()
        try:
            with patch.object(window, "open_camera_viewer") as picker, patch.object(
                    window.worker, "submit") as submit:
                window.composer.setPlainText("Yuna, mostre a câmera da garagem")
                window.send_message()
                picker.assert_called_once()
                submit.assert_not_called()
        finally:
            window.close()


if __name__ == "__main__":
    unittest.main()
