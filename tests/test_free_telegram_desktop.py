"""Teste Qt sem mensagens reais ou credenciais persistentes."""
import importlib.util
import os
import time
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

TOKEN = "123456789:" + "x"*35
CHAT = "123456789"


@unittest.skipUnless(importlib.util.find_spec("PySide6"), "Qt opcional")
class TelegramSafetyUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def create_widget(self):
        from home_safety_dialog import HomeSafetyDialog
        w = HomeSafetyDialog()
        w.recipient.setText("5534999999999")
        return w

    def enable_telegram_form(self, widget):
        widget.telegram_checkbox.setChecked(True)
        widget.telegram_bot_token.setText(TOKEN)
        widget.telegram_chat_id.setText(CHAT)

    def activate_with_approval(self, widget):
        from PySide6.QtWidgets import QMessageBox
        with patch("home_safety_dialog.QMessageBox.question",
                   return_value=QMessageBox.StandardButton.Yes):
            widget.activate_safety()

    def test_off_by_default_and_no_auto_network(self):
        from PySide6.QtWidgets import QMessageBox
        w = self.create_widget()
        try:
            self.assertFalse(w.active)
            self.assertFalse(w.telegram_checkbox.isChecked())
            self.assertFalse(w.telegram_bot_token.isEnabled())
            self.assertIsNone(w._telegram_notifier)
            with patch("home_safety_dialog.QMessageBox.question",
                       return_value=QMessageBox.StandardButton.No), patch(
                       "home_safety_dialog.FreeTelegramNotifier") as telegram:
                self.enable_telegram_form(w)
                w.activate_safety()
                telegram.assert_called_once()
            self.assertFalse(w.active)
        finally:
            w.close()

    def test_invalid_credentials_rejected_before_consent(self):
        w = self.create_widget()
        try:
            w.telegram_checkbox.setChecked(True)
            w.telegram_bot_token.setText("bad-token")
            w.telegram_chat_id.setText(CHAT)
            with patch("home_safety_dialog.QMessageBox.question") as question:
                w.activate_safety()
                question.assert_not_called()
            self.assertFalse(w.active)
            self.assertIn("Configure o bot", w.warning.text())
        finally:
            w.close()

    def test_sos_sends_only_after_confirmation_and_provider_acceptance(self):
        from PySide6.QtWidgets import QMessageBox
        w = self.create_widget()
        try:
            self.enable_telegram_form(w)
            self.activate_with_approval(w)
            self.assertTrue(w.active)
            self.assertIn("Telegram", w.sos.text())
            with patch("home_safety_dialog.QMessageBox.question",
                       return_value=QMessageBox.StandardButton.No), patch(
                       "home_safety_dialog.FreeTelegramNotifier.send_event") as sender:
                w.send_sos_draft()
                sender.assert_not_called()
            # Thread start is replaced with local synchronous test execution.
            def thread_factory(*_args, **kwargs):
                mocked = MagicMock()
                mocked.start.side_effect = kwargs["target"]
                return mocked

            with patch("home_safety_dialog.QMessageBox.question",
                       return_value=QMessageBox.StandardButton.Yes), patch(
                       "home_safety_dialog.FreeTelegramNotifier.send_event",
                       return_value=True) as sender, patch(
                       "home_safety_dialog.threading.Thread",
                       side_effect=thread_factory):
                w.send_sos_draft()
                self.app.processEvents()
                sender.assert_called_once_with("sos")
                self.assertIn("aceitou", w.warning.text())
                self.assertEqual(w._alert_budget.remaining, 5)
                # Even if pressed repeatedly, the cooldown prevents spam.
                w.send_sos_draft()
                self.app.processEvents()
                sender.assert_called_once()
            w.stop_safety()
            self.assertFalse(w.active)
            self.assertEqual(w.telegram_bot_token.text(), "")
            self.assertFalse(w._audio_mode)
        finally:
            w.close()

    def test_sound_alert_can_go_out_after_grace_without_manual_send(self):
        w = self.create_widget()
        try:
            self.enable_telegram_form(w)
            self.activate_with_approval(w)
            self.assertTrue(w.active)
            w._pending.schedule(now=time.monotonic()-20)
            def immediate_thread(*_args, **kwargs):
                mock = MagicMock()
                mock.start.side_effect = kwargs["target"]
                return mock
            with patch("home_safety_dialog.FreeTelegramNotifier.send_event",
                       return_value=True) as sender, patch(
                       "home_safety_dialog.threading.Thread",
                       side_effect=immediate_thread), patch.object(
                       w, "_offer_whatsapp_draft") as whatsapp:
                w._tick()
                self.app.processEvents()
                sender.assert_called_once_with("som_alto")
                whatsapp.assert_not_called()
                self.assertFalse(w._pending.pending)
        finally:
            w.close()

    def test_stop_prevents_queued_send_or_stale_result(self):
        w = self.create_widget()
        try:
            self.enable_telegram_form(w)
            self.activate_with_approval(w)
            tasks = []
            def delayed_thread(*_args, **kwargs):
                mock = MagicMock()
                mock.start.side_effect = lambda: tasks.append(kwargs["target"])
                return mock
            with patch("home_safety_dialog.threading.Thread",
                       side_effect=delayed_thread), patch(
                       "home_safety_dialog.FreeTelegramNotifier.send_event") as sender:
                self.assertTrue(w._send_telegram_event("sos"))
                self.assertEqual(len(tasks), 1)
                old_epoch = w._notification_epoch
                w.stop_safety()
                tasks[0]()
                sender.assert_not_called()
                w._on_telegram_result(old_epoch, True)
                self.assertNotIn("Telegram aceitou", w.warning.text())
        finally:
            w.close()


if __name__ == "__main__":
    unittest.main()
