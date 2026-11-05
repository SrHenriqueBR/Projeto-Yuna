"""Teste real da bandeja Qt em ambiente sem tela, sem ligar webcam/IA."""
import importlib.util
import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
QT = importlib.util.find_spec("PySide6") is not None


@unittest.skipUnless(QT, "PySide6 não disponível")
class TrayControllerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        from yuna_desktop import YunaDesktop
        with patch("yuna_desktop.DesktopWorker.start"), patch(
                "compact_chat.QSystemTrayIcon.isSystemTrayAvailable",
                return_value=False):
            self.window = YunaDesktop()
        self.ctrl = self.window.companion
        self.window.battery_timer.stop()
        self.window.unreal_heartbeat.stop()

    def tearDown(self):
        self.ctrl.closing = True
        self.ctrl.tray_available = False
        self.window.close()
        self.app.processEvents()

    def test_icons_menu_and_low_resource_mode(self):
        self.assertEqual(set(self.ctrl.mode_actions), {
            "ativa", "economica", "acompanhamento", "pausada"})
        self.ctrl.set_mode("economica")
        self.assertEqual(self.ctrl.mode, "economica")
        self.assertEqual(self.ctrl.timer.interval(), 1200)
        self.assertEqual(self.window.battery_timer.interval(), 300000)
        self.assertFalse(self.window.unreal_heartbeat.isActive())
        self.assertTrue(self.ctrl.mode_actions["economica"].isChecked())
        self.assertIn("Modo econômico", self.ctrl.tray.toolTip())
        self.assertNotIn("microfone", self.ctrl.tray.toolTip())
        self.ctrl.set_mode("ativa")
        self.assertEqual(self.ctrl.timer.interval(), 200)
        self.assertEqual(self.window.battery_timer.interval(), 90000)
        self.assertTrue(self.window.unreal_heartbeat.isActive())

    def test_monitoring_opt_in_does_not_open_mic_or_camera_or_ask_model(self):
        with patch("compact_chat.sys.platform", "win32"), patch.object(
                self.ctrl.plugs, "start") as start, patch.object(
                self.window, "open_camera_viewer") as camera, patch.object(
                self.window.worker, "submit") as llm, patch(
                "compact_chat.QMessageBox.question") as prompt:
            self.ctrl.plug_action.setChecked(False)
            self.ctrl.set_mode("acompanhamento")
            self.assertTrue(self.ctrl.plug_action.isChecked())
            self.assertEqual(self.ctrl.mode, "acompanhamento")
            start.assert_called()
            self.assertFalse(self.ctrl.wake_action.isChecked())
            self.assertEqual(self.ctrl.timer.interval(), 1000)
            self.assertEqual(self.window.battery_timer.interval(), 180000)
            self.assertFalse(self.window.unreal_heartbeat.isActive())
            self.assertTrue(self.ctrl.health_timer.isActive())
            self.assertEqual(self.ctrl.health_timer.interval(), 300000)
            camera.assert_not_called()
            llm.assert_not_called()
            prompt.assert_not_called()
        self.assertIn("Acompanhamento leve", self.ctrl.tray.toolTip())

    def test_pausing_cancels_tasks_and_stops_verifications(self):
        with patch.object(self.window, "emergency_stop", wraps=self.window.emergency_stop) as halt:
            self.ctrl.set_mode("pausada")
            halt.assert_called_once()
        self.assertEqual(self.ctrl.mode, "pausada")
        self.assertFalse(self.window.battery_timer.isActive())
        self.assertFalse(self.ctrl.health_timer.isActive())
        self.assertFalse(self.window.unreal_heartbeat.isActive())
        self.assertFalse(self.ctrl.plugs.active)
        self.assertFalse(self.ctrl.wake_action.isChecked())
        self.assertIn("Pausada", self.ctrl.tray.toolTip())
        with patch.object(self.ctrl.panel, "show_panel"):
            self.ctrl.show_compact()
        self.assertEqual(self.ctrl.mode, "ativa")

    def test_recolher_moves_to_eco_without_quitting(self):
        self.ctrl.tray_available = True
        self.ctrl.set_mode("ativa")
        self.ctrl.on_recolher()
        self.assertEqual(self.ctrl.mode, "economica")
        self.assertFalse(self.ctrl.closing)
        self.ctrl.set_mode("acompanhamento")
        self.ctrl.on_recolher()
        self.assertEqual(self.ctrl.mode, "acompanhamento")
        self.ctrl.tray_available = False

    def test_health_monitor_reads_only_in_opt_in_mode(self):
        from health_watch import HealthReading
        self.ctrl.tray_available = False
        with patch("compact_chat.read_health",
                   return_value=HealthReading(96, 33, 30)) as read, patch.object(
                self.window, "add_message") as chat, patch.object(
                self.window.worker, "submit") as model:
            self.ctrl._health_tick()
            read.assert_not_called()
            self.ctrl.set_mode("acompanhamento")
            self.ctrl._health_tick()
            self.ctrl._health_tick()
            self.assertEqual(read.call_count, 2)
            chat.assert_called_once()
            self.assertIn("RAM", chat.call_args.args[1])
            model.assert_not_called()
            self.ctrl.set_mode("economica")
            self.ctrl._health_tick()
            self.assertEqual(read.call_count, 2)
            self.assertFalse(self.ctrl.health_timer.isActive())

    def test_no_toast_or_model_when_economy_or_paused(self):
        for mode in ("economica", "pausada"):
            self.ctrl.set_mode(mode)
            with patch.object(self.window, "add_message") as chat, patch.object(
                    self.window.worker, "record") as history, patch.object(
                    self.window.worker, "submit") as model:
                self.ctrl.connection_notice("Controle conectado")
                chat.assert_not_called()
                history.assert_not_called()
                model.assert_not_called()


if __name__ == "__main__":
    unittest.main()
