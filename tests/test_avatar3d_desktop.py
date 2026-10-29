"""Integração da ponte de avatar com Qt (offscreen e sem abrir navegador)."""
import importlib.util
import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@unittest.skipUnless(importlib.util.find_spec("PySide6"), "PySide6 opcional")
class Avatar3DDesktopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def _desktop(self):
        from yuna_desktop import YunaDesktop
        with patch("yuna_desktop.DesktopWorker.start"):
            return YunaDesktop()

    def test_does_not_open_network_port_by_default(self):
        window = self._desktop()
        try:
            self.assertIsNone(window.avatar_bridge)
            self.assertIn("Conectar Yuna 3D", window.avatar3d_button.text())
        finally:
            window.close()

    def test_bridge_connects_and_receives_live_audio_events(self):
        window = self._desktop()
        try:
            with patch("yuna_desktop.socket.create_connection"), patch(
                    "yuna_desktop.QDesktopServices.openUrl", return_value=True), patch(
                    "yuna_desktop.Avatar3DBridge") as bridge_factory:
                bridge = bridge_factory.return_value
                bridge.start.return_value = bridge
                bridge.viewer_url.return_value = (
                    "http://127.0.0.1:5173/#bridgePort=54321&bridgeToken="
                    + "x" * 43
                )
                window.toggle_avatar3d_bridge()
                self.assertIs(window.avatar_bridge, bridge)
                self.assertIn("Desconectar", window.avatar3d_button.text())
                window._avatar_event("avatar.pose", pose="happy")
                bridge.publish.assert_called()
                window._avatar_event("speech.started", speech_id="7")
                # MP3 não possui amostras WAV: amplitude desconhecida não quebra o Qt.
                self.assertTrue(window._avatar_event(
                    "speech.level", speech_id="7",
                    position_ms=150, amplitude=None
                ))
                self.assertTrue(window.avatar_controller.snapshot.speaking)
                window._avatar_event("speech.interrupted", speech_id="7")
                self.assertFalse(window.avatar_controller.snapshot.speaking)
                self.assertEqual(window.avatar_controller.snapshot.mouth_level, 0)
                window.toggle_avatar3d_bridge()
                bridge.stop.assert_called_once()
                self.assertIsNone(window.avatar_bridge)
        finally:
            window.close()

    def test_local_preview_missing_keeps_bridge_disabled(self):
        window = self._desktop()
        try:
            with patch("yuna_desktop.socket.create_connection",
                       side_effect=ConnectionRefusedError()), patch(
                       "yuna_desktop.QMessageBox.information") as info:
                window.toggle_avatar3d_bridge()
            self.assertIsNone(window.avatar_bridge)
            info.assert_called_once()
        finally:
            window.close()

    def test_browser_failure_closes_server(self):
        window = self._desktop()
        try:
            with patch("yuna_desktop.socket.create_connection"), patch(
                    "yuna_desktop.QDesktopServices.openUrl", return_value=False), patch(
                    "yuna_desktop.Avatar3DBridge") as factory:
                bridge = factory.return_value
                bridge.start.return_value = bridge
                window.toggle_avatar3d_bridge()
                self.assertIsNone(window.avatar_bridge)
                bridge.stop.assert_called_once()
        finally:
            window.close()


if __name__ == "__main__":
    unittest.main()
