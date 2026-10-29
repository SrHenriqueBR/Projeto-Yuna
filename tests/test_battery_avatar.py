"""Avatar Qt reage à bateria de forma local, sem Ollama, GPU ou Windows real."""
import importlib.util
import os
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from battery_life import BatteryStatus

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@unittest.skipUnless(importlib.util.find_spec("PySide6"), "PySide6 opcional")
class BatteryAvatarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def _avatar(self, folder):
        from hardware_profiles import PROFILES
        from yuna_avatar import YunaAvatar
        with patch("yuna_avatar.YunaAvatar._animation_profile",
                   return_value=PROFILES["leve"]):
            return YunaAvatar(Path(folder))

    def test_low_battery_sleepy_and_power_saving(self):
        with tempfile.TemporaryDirectory() as folder:
            avatar = self._avatar(folder)
            try:
                avatar.set_battery_status(BatteryStatus(17, False))
                self.assertEqual(avatar.battery_mood.mode, "low")
                self.assertEqual(avatar.visible_pose(), "sleepy")
                self.assertIn("17%", avatar.bubble)
                self.assertGreaterEqual(avatar.animation.interval(), 80)
                avatar.set_battery_status(BatteryStatus(17, True))
                self.assertEqual(avatar.visible_pose(), "sit")
                self.assertFalse(avatar.battery_mood.seek_charger)
                avatar.set_battery_status(None)
                self.assertIsNone(avatar.battery_mood.percent)
            finally:
                avatar.close()

    def test_full_charge_happy_without_autoplay(self):
        with tempfile.TemporaryDirectory() as folder:
            avatar = self._avatar(folder)
            try:
                avatar.set_battery_status(BatteryStatus(100, True))
                self.assertEqual(avatar.battery_mood.mode, "full")
                self.assertEqual(avatar.visible_pose(), "happy")
                self.assertIn("100%", avatar.bubble)
                self.assertFalse(hasattr(avatar, "game_controller"))
            finally:
                avatar.close()

    def test_speaking_and_manual_pose_override_battery_sleep(self):
        with tempfile.TemporaryDirectory() as folder:
            avatar = self._avatar(folder)
            try:
                avatar.set_pose("wave", seconds=30)
                avatar.set_battery_status(BatteryStatus(8, False))
                self.assertEqual(avatar.visible_pose(), "wave")
                avatar.pose_until = 0
                avatar.set_speaking(True)
                self.assertEqual(avatar.visible_pose(), "talk")
                avatar.set_speaking(False)
                self.assertEqual(avatar.visible_pose(), "sleepy")
            finally:
                avatar.close()

    def test_manual_refresh_uses_injected_sensor(self):
        with tempfile.TemporaryDirectory() as folder:
            avatar = self._avatar(folder)
            try:
                with patch("yuna_avatar.read_battery",
                           return_value=BatteryStatus(30, False)):
                    avatar.refresh_battery_state()
                self.assertEqual(avatar.battery_mood.mode, "tired")
            finally:
                avatar.close()


@unittest.skipUnless(importlib.util.find_spec("PySide6"), "PySide6 opcional")
class BatteryDesktopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_alert_once_and_sync_bridge(self):
        from yuna_desktop import YunaDesktop
        with patch("yuna_desktop.DesktopWorker.start"):
            window = YunaDesktop()
        try:
            with patch("yuna_desktop.read_battery", return_value=BatteryStatus(18, False)), patch.object(
                window, "add_message") as message:
                window.poll_battery()
                self.assertEqual(window._battery_mood.mode, "low")
                message.assert_called_once()
                window.poll_battery()
                message.assert_called_once()
            from unittest.mock import Mock
            bridge = Mock()
            window.avatar_bridge = bridge
            with patch("yuna_desktop.read_battery", return_value=BatteryStatus(100, True)):
                window.poll_battery()
            self.assertEqual(bridge.publish.call_args.kwargs["battery"]["mode"], "full")
            self.assertEqual(bridge.publish.call_args.kwargs["battery"]["percent"], 100)
            window.avatar_bridge = None
        finally:
            window.close()


if __name__ == "__main__":
    unittest.main()
