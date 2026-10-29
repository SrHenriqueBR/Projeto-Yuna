"""A Yuna só exibe convite e abre navegador depois de ações explícitas."""
import importlib.util
import os
import unittest
from unittest.mock import patch, sentinel

from remote_camera_invite import new_remote_camera_invite

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@unittest.skipUnless(importlib.util.find_spec("PySide6"), "Qt opcional")
class RemoteCameraQtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def _desktop(self):
        from yuna_desktop import YunaDesktop
        with patch("yuna_desktop.DesktopWorker.start"):
            return YunaDesktop()

    def test_command_opens_only_invitation_wizard(self):
        window = self._desktop()
        try:
            with patch.object(window, "open_remote_camera_invitation") as wizard, patch.object(
                    window.worker, "submit") as submit, patch(
                    "yuna_desktop.QDesktopServices.openUrl") as browser:
                window.composer.setPlainText("Magi1020")
                window.send_message()
                wizard.assert_called_once_with()
                submit.assert_not_called()
                browser.assert_not_called()
            self.assertIsNone(window.camera_viewer)
        finally:
            window.close()

    def test_cancel_does_not_open_browser_or_camera(self):
        window = self._desktop()
        try:
            with patch("yuna_desktop.QInputDialog.getItem",
                       return_value=("", False)), patch(
                       "yuna_desktop.QDesktopServices.openUrl") as open_url, patch(
                       "yuna_desktop.QApplication.clipboard") as clipboard:
                window.open_remote_camera_invitation()
                open_url.assert_not_called()
                clipboard.assert_not_called()
            self.assertIsNone(window.camera_viewer)
        finally:
            window.close()

    def test_recipient_must_choose_to_open_link_in_browser(self):
        from PySide6.QtWidgets import QMessageBox
        window = self._desktop()
        link = new_remote_camera_invite()
        try:
            with patch("yuna_desktop.QInputDialog.getItem",
                       return_value=("Entrar com um convite que recebi", True)), patch(
                       "yuna_desktop.QInputDialog.getText",
                       return_value=(link, True)), patch(
                       "yuna_desktop.QMessageBox.question",
                       return_value=QMessageBox.StandardButton.Yes), patch(
                       "yuna_desktop.QDesktopServices.openUrl",
                       return_value=True) as browser:
                window.open_remote_camera_invitation()
                browser.assert_called_once()
                self.assertEqual(browser.call_args.args[0].toString(), link)
            self.assertIsNone(window.camera_viewer)
        finally:
            window.close()

    def test_declined_recipient_request_never_opens_browser(self):
        from PySide6.QtWidgets import QMessageBox
        window = self._desktop()
        link = new_remote_camera_invite()
        try:
            with patch("yuna_desktop.QInputDialog.getItem",
                       return_value=("Entrar com um convite que recebi", True)), patch(
                       "yuna_desktop.QInputDialog.getText",
                       return_value=(link, True)), patch(
                       "yuna_desktop.QMessageBox.question",
                       return_value=QMessageBox.StandardButton.No), patch(
                       "yuna_desktop.QDesktopServices.openUrl") as browser:
                window.open_remote_camera_invitation()
                browser.assert_not_called()
        finally:
            window.close()

    def test_invalid_invite_never_opens_website(self):
        window = self._desktop()
        try:
            with patch("yuna_desktop.QInputDialog.getItem",
                       return_value=("Entrar com um convite que recebi", True)), patch(
                       "yuna_desktop.QInputDialog.getText",
                       return_value=("https://other-site.example/room", True)), patch(
                       "yuna_desktop.QMessageBox.warning") as warning, patch(
                       "yuna_desktop.QDesktopServices.openUrl") as browser:
                window.open_remote_camera_invitation()
                browser.assert_not_called()
                warning.assert_called_once()
        finally:
            window.close()

    def test_creator_must_explicitly_click_copy_or_open(self):
        window = self._desktop()
        link = new_remote_camera_invite()
        try:
            with patch("yuna_desktop.QInputDialog.getItem",
                       return_value=("Criar convite privado para minha esposa", True)), patch(
                       "yuna_desktop.new_remote_camera_invite",
                       return_value=link), patch(
                       "yuna_desktop.QMessageBox") as dialog, patch(
                       "yuna_desktop.QApplication.clipboard") as clipboard, patch(
                       "yuna_desktop.QDesktopServices.openUrl") as browser:
                box = dialog.return_value
                box.addButton.side_effect = [
                    sentinel.copy, sentinel.copy_open, sentinel.cancel
                ]
                box.clickedButton.return_value = sentinel.copy_open
                browser.return_value = True
                window.open_remote_camera_invitation()
                clipboard.return_value.setText.assert_called_once_with(link)
                browser.assert_called_once()
                self.assertEqual(browser.call_args.args[0].toString(), link)
        finally:
            window.close()


if __name__ == "__main__":
    unittest.main()
