"""Testes do UI autorizável sem câmera, rede, microfone ou serviço Jitsi real."""
import importlib.util
import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@unittest.skipUnless(importlib.util.find_spec("PySide6"), "PySide6 opcional")
class SafetyQtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_safety_mode_is_off_and_requires_explicit_approval(self):
        from PySide6.QtWidgets import QMessageBox
        from home_safety_dialog import HomeSafetyDialog
        widget = HomeSafetyDialog()
        try:
            self.assertFalse(widget.active)
            self.assertFalse(widget.sos.isEnabled())
            widget.recipient.setText("5534999999999")
            widget.sound_checkbox.setChecked(True)
            with patch("home_safety_dialog.QMessageBox.question",
                       return_value=QMessageBox.StandardButton.No), patch.object(
                       widget, "_start_microphone") as audio:
                widget.activate_safety()
                audio.assert_not_called()
            self.assertFalse(widget.active)
            with patch("home_safety_dialog.QMessageBox.question",
                       return_value=QMessageBox.StandardButton.Yes), patch.object(
                       widget, "_start_microphone", return_value=True):
                widget.activate_safety()
            self.assertTrue(widget.active)
            self.assertTrue(widget.sos.isEnabled())
            self.assertIn("ATIVA", widget.windowTitle())
            widget.stop_safety()
            self.assertFalse(widget.active)
        finally:
            widget.close()

    def test_sos_only_opens_whatsapp_after_manual_confirmation(self):
        from PySide6.QtWidgets import QMessageBox
        from home_safety_dialog import HomeSafetyDialog
        widget = HomeSafetyDialog()
        try:
            widget.recipient.setText("5534999999999")
            with patch("home_safety_dialog.QMessageBox.question",
                       return_value=QMessageBox.StandardButton.Yes):
                widget.activate_safety()
            self.assertTrue(widget.active)
            self.assertFalse(widget._audio_mode)
            with patch("home_safety_dialog.QMessageBox.question",
                       return_value=QMessageBox.StandardButton.No), patch(
                       "home_safety_dialog.QDesktopServices.openUrl") as open_url:
                widget.send_sos_draft()
                open_url.assert_not_called()
            with patch("home_safety_dialog.QMessageBox.question",
                       return_value=QMessageBox.StandardButton.Yes), patch(
                       "home_safety_dialog.QDesktopServices.openUrl",
                       return_value=True) as open_url:
                widget.send_sos_draft()
                open_url.assert_called_once()
                self.assertTrue(
                    open_url.call_args.args[0].toString().startswith("https://wa.me/")
                )
        finally:
            widget.close()

    def test_loud_sound_grace_period_can_be_cancelled(self):
        from PySide6.QtWidgets import QMessageBox
        from home_safety_dialog import HomeSafetyDialog
        widget = HomeSafetyDialog()
        try:
            widget.recipient.setText("5534999999999")
            with patch("home_safety_dialog.QMessageBox.question",
                       return_value=QMessageBox.StandardButton.Yes):
                widget.activate_safety()
            widget._pending.schedule(now=100, delay=15)
            widget.cancel_sound_alert()
            with patch.object(widget, "_offer_whatsapp_draft") as offer:
                widget._tick()
                offer.assert_not_called()
        finally:
            widget.close()

    def test_desktop_stop_disables_monitoring_and_video(self):
        from PySide6.QtWidgets import QMessageBox
        from yuna_desktop import YunaDesktop
        with patch("yuna_desktop.DesktopWorker.start"):
            window = YunaDesktop()
        try:
            self.assertIsNone(window.home_safety_dialog)
            self.assertIsNone(window.embedded_video)
            window.open_home_safety()
            dialog = window.home_safety_dialog
            self.assertIsNotNone(dialog)
            self.assertFalse(dialog.active)
            dialog.recipient.setText("5534999999999")
            with patch("home_safety_dialog.QMessageBox.question",
                       return_value=QMessageBox.StandardButton.Yes):
                dialog.activate_safety()
            self.assertTrue(dialog.active)
            self.assertIn("Segurança ATIVA", window.safety_button.text())
            window.emergency_stop()
            self.assertFalse(dialog.active)
            self.assertIn("Segurança doméstica (SOS)", window.safety_button.text())
        finally:
            window.close()

    def test_embedded_meeting_denies_untrusted_origin(self):
        from PySide6.QtCore import QUrl
        from embedded_video import EmbeddedVideoDialog
        from remote_camera_invite import new_remote_camera_invite
        # Impede inicialização real do Qt WebEngine no runner CI.
        with patch.dict("sys.modules", {"PySide6.QtWebEngineWidgets": None}):
            window = EmbeddedVideoDialog(new_remote_camera_invite())
        try:
            from unittest.mock import Mock
            bad_permission = Mock()
            bad_permission.origin.return_value = QUrl("https://attacker.example")
            bad_permission.permissionType.return_value.name = "MediaVideoCapture"
            window._request_permission(bad_permission)
            bad_permission.deny.assert_called_once()
            bad_permission.grant.assert_not_called()
            self.assertFalse(window.start())
        finally:
            window.close()

    def test_request_to_view_inside_yuna_requires_confirmation(self):
        from PySide6.QtWidgets import QMessageBox
        from yuna_desktop import YunaDesktop
        from remote_camera_invite import new_remote_camera_invite
        with patch("yuna_desktop.DesktopWorker.start"):
            window = YunaDesktop()
        try:
            invite = new_remote_camera_invite()
            with patch("yuna_desktop.QInputDialog.getText",
                       return_value=(invite, True)), patch(
                       "yuna_desktop.QMessageBox.question",
                       return_value=QMessageBox.StandardButton.No), patch.object(
                       window, "open_embedded_video") as open_view:
                window.request_embedded_video()
                open_view.assert_not_called()
            with patch("yuna_desktop.QInputDialog.getText",
                       return_value=(invite, True)), patch(
                       "yuna_desktop.QMessageBox.question",
                       return_value=QMessageBox.StandardButton.Yes), patch.object(
                       window, "open_embedded_video") as open_view:
                window.request_embedded_video()
                open_view.assert_called_once_with(invite)
        finally:
            window.close()
