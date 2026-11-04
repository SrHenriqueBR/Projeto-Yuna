import importlib.util
import os
from threading import Event
import time
import unittest
from unittest.mock import Mock, patch

from plug_sense import PlugSnapshot
from usb_devices import USBDevice

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@unittest.skipUnless(importlib.util.find_spec("PySide6"), "Qt opcional")
class PlugMonitorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        from plug_monitor import PlugMonitor
        self.reader = Mock(return_value=PlugSnapshot((), True))
        self.monitor = PlugMonitor(reader=self.reader)
        self.messages = []
        self.monitor.notice.connect(self.messages.append)
        with patch("plug_monitor.sys.platform", "win32"):
            self.monitor.start()
        self.monitor.debounce.stop()

    def tearDown(self):
        self.monitor.stop()
        self.app.processEvents()
        self.monitor.deleteLater()

    def deliver(self, usb=(), power=True):
        self.monitor._received(self.monitor.generation, PlugSnapshot(usb, power))

    def wait_until(self, predicate):
        from PySide6.QtTest import QTest
        deadline = time.monotonic() + 3
        while not predicate() and time.monotonic() < deadline:
            QTest.qWait(10)
        self.assertTrue(predicate())

    def test_real_thread_delivery_keeps_initial_snapshot_silent(self):
        self.monitor._refresh()
        self.wait_until(lambda: self.monitor.snapshot is not None)
        self.assertEqual(self.messages, [])
        self.reader.return_value = PlugSnapshot((USBDevice("id", "Mouse"),), False)
        changed = Mock()
        self.monitor.power_changed.connect(changed)
        self.monitor._refresh()
        self.wait_until(lambda: bool(self.messages))
        self.assertIn("Mouse", self.messages[0])
        self.assertIn("desconectada", self.messages[0])
        changed.assert_called_once_with()

    def test_native_burst_is_debounced_without_io_in_callback(self):
        for _ in range(100):
            self.monitor.native_event(0x219, 7)
        self.assertTrue(self.monitor.debounce.isActive())
        self.reader.assert_not_called()
        self.monitor.debounce.stop()
        self.monitor.native_event(0x219, 0x8001)  # query removal: never interfere
        self.assertFalse(self.monitor.debounce.isActive())
        self.monitor.native_event(0x218, 0x0A)
        self.assertTrue(self.monitor.debounce.isActive())

    def test_only_one_worker_and_one_pending_refresh(self):
        release = Event()
        entered = Event()
        def read():
            entered.set()
            release.wait(3)
            return PlugSnapshot((), True)
        self.reader.side_effect = read
        try:
            self.monitor._refresh()
            self.wait_until(entered.is_set)
            for _ in range(5):
                self.monitor._refresh()
                self.monitor.request_refresh()
            self.assertEqual(self.reader.call_count, 1)
            release.set()
            self.wait_until(lambda: self.monitor.inflight is None)
            self.assertTrue(self.monitor.debounce.isActive())
        finally:
            release.set()

    def test_paused_or_late_results_do_not_reactivate(self):
        self.deliver()
        generation = self.monitor.generation
        self.monitor.stop()
        self.monitor._received(generation, PlugSnapshot((USBDevice("id"),), False))
        self.monitor.native_event(0x219, 7)
        self.assertFalse(self.monitor.debounce.isActive())
        self.assertIsNone(self.monitor.snapshot)
        self.assertFalse(self.messages)

    def test_resume_rebaselines_and_discards_pre_suspend_result(self):
        self.deliver((USBDevice("old"),))
        generation = self.monitor.generation
        self.monitor.native_event(0x218, 4)
        self.monitor.request_refresh()
        self.assertFalse(self.monitor.debounce.isActive())
        self.monitor.native_event(0x218, 0x12)
        self.monitor._received(generation, PlugSnapshot((), False))
        self.assertIsNone(self.monitor.snapshot)
        self.deliver((USBDevice("new"),), False)
        self.assertFalse(self.messages)

    def test_failed_worker_does_not_report_everything_unplugged(self):
        self.deliver((USBDevice("old"),))
        self.reader.side_effect = OSError("driver indisponível")
        self.monitor._refresh()
        self.wait_until(lambda: self.monitor.inflight is None)
        self.assertEqual(self.monitor.snapshot, PlugSnapshot(None, None))
        self.assertFalse(self.messages)


@unittest.skipUnless(importlib.util.find_spec("PySide6"), "Qt opcional")
class PlugDesktopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        from yuna_desktop import YunaDesktop
        with patch("yuna_desktop.DesktopWorker.start"), patch(
                "compact_chat.QSystemTrayIcon.isSystemTrayAvailable", return_value=False):
            self.window = YunaDesktop()
        self.window.battery_timer.stop()
        self.window.voice_index = 0
        self.controller = self.window.companion
        self.controller.plugs.active = True

    def tearDown(self):
        self.controller.closing = True
        self.window.close()
        self.app.processEvents()

    def test_notice_is_text_only_by_default_and_not_model_or_memory(self):
        with patch.object(self.window.worker, "record") as record, patch.object(
                self.window.worker, "submit") as model, patch.object(self.window, "say") as voice:
            self.controller.connection_notice("Percebi <script>um mouse</script>.")
        self.assertIn("<script>um mouse</script>", self.controller.panel.messages.toPlainText())
        record.assert_not_called()
        model.assert_not_called()
        voice.assert_not_called()

    def test_voice_opt_in_never_interrupts_and_stop_mutes_it(self):
        self.controller.plug_voice.setChecked(True)
        with patch.object(self.window, "say") as voice:
            self.controller.connection_notice("Mouse conectado")
            voice.assert_called_once_with("Mouse conectado")
            voice.reset_mock()
            self.window.voice_busy = True
            self.controller.connection_notice("Teclado conectado")
            self.window.voice_busy = False
            self.window.set_busy(True)
            self.controller.connection_notice("Controle conectado")
            self.window.set_busy(False)
            self.window.microphone_busy = True
            self.controller.connection_notice("Energia externa conectada")
            self.window.microphone_busy = False
            voice.assert_not_called()
        self.controller.stop()
        self.assertFalse(self.controller.plug_voice.isChecked())

    def test_edge_voice_gets_no_device_metadata_or_power_state(self):
        self.window.voice_index = 2
        self.controller.plug_voice.setChecked(True)
        with patch.object(self.window, "say") as voice:
            self.controller.connection_notice("Pendrive da Maria; energia desconectada")
            voice.assert_called_once_with("Confira as conexões do computador no chat.")

    def test_status_is_deterministic_not_sent_to_model_or_history(self):
        self.controller.plugs.snapshot = PlugSnapshot((USBDevice("private", "Controle", True),), True)
        with patch("compact_chat.sys.platform", "win32"), patch.object(
                self.window.worker, "record") as record, patch.object(
                self.window.worker, "submit") as model, patch.object(self.window, "say"):
            self.assertTrue(self.controller.handle("Yuna, mostre as conexões"))
        text = self.controller.panel.messages.toPlainText()
        self.assertIn("Controle (USB-C)", text)
        self.assertNotIn("private", text)
        record.assert_not_called()
        model.assert_not_called()

    def test_background_notification_keeps_focus_and_pause_stops_observation(self):
        self.controller.tray_available = True
        with patch.object(self.controller.tray, "showMessage") as toast, patch.object(
                self.controller, "show_compact") as show:
            self.controller.connection_notice("Controle conectado")
            toast.assert_called_once()
            show.assert_not_called()
        self.controller.toggle_plugs(False)
        self.assertFalse(self.controller.plugs.active)
        with patch.object(self.window, "add_message") as message:
            self.controller.connection_notice("aviso atrasado")
            message.assert_not_called()

    def test_existing_battery_charging_notice_not_duplicated(self):
        from battery_life import BatteryStatus
        with patch("yuna_desktop.read_battery", return_value=BatteryStatus(50, True)), patch.object(
                self.window, "add_message") as message:
            self.window.poll_battery()
            message.assert_not_called()
        self.assertEqual(self.window._battery_mood.mode, "charging")
        with patch("yuna_desktop.read_battery", return_value=BatteryStatus(10, False)), patch.object(
                self.window, "add_message") as message:
            self.window.poll_battery()
            self.assertIn("10%", message.call_args.args[1])


if __name__ == "__main__":
    unittest.main()
