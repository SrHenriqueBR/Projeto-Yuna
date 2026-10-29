import unittest
from unittest.mock import Mock, patch

from battery_life import (
    BatteryStatus, BatteryCompanion, classify,
    public_battery, read_battery,
)


class BatteryLifeTests(unittest.TestCase):
    def test_thresholds_and_charger_override(self):
        cases = [
            (None, "unavailable"),
            (BatteryStatus(0, False), "critical"),
            (BatteryStatus(10, False), "critical"),
            (BatteryStatus(11, False), "low"),
            (BatteryStatus(20, False), "low"),
            (BatteryStatus(21, False), "tired"),
            (BatteryStatus(35, False), "tired"),
            (BatteryStatus(36, False), "normal"),
            (BatteryStatus(100, False), "normal"),
            (BatteryStatus(4, True), "charging"),
            (BatteryStatus(99, True), "charging"),
            (BatteryStatus(100, True), "full"),
        ]
        for state, expected in cases:
            with self.subTest(state=state):
                self.assertEqual(classify(state), expected)

    def test_battery_validation(self):
        for value in (-1, 101, True, "15", None):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    BatteryStatus(value, False)
        with self.assertRaises(ValueError):
            BatteryStatus(55, 1)

    def test_tired_low_critical_then_recharge_and_full(self):
        companion = BatteryCompanion()
        tired = companion.observe(BatteryStatus(34, False), now=10)
        self.assertEqual(tired.pose, "sit")
        self.assertIn("34%", tired.announcement)
        low = companion.observe(BatteryStatus(18, False), now=20)
        self.assertEqual(low.pose, "sleepy")
        self.assertTrue(low.seek_charger)
        self.assertEqual(low.fps_cap, 12)
        self.assertIn("carregador", low.announcement)
        critical = companion.observe(BatteryStatus(8, False), now=30)
        self.assertIn("8%", critical.announcement)
        self.assertFalse(companion.observe(BatteryStatus(8, False), now=31).announcement)
        charging = companion.observe(BatteryStatus(8, True), now=50)
        self.assertEqual(charging.mode, "charging")
        self.assertFalse(charging.seek_charger)
        self.assertIn("Carregador", charging.announcement)
        full = companion.observe(BatteryStatus(100, True), now=70)
        self.assertTrue(full.suggested_activity)
        self.assertEqual(full.pose, "happy")
        self.assertIn("100%", full.announcement)
        self.assertFalse(companion.observe(BatteryStatus(100, True), now=75).announcement)

    def test_no_repeated_notifications_on_fluctuation(self):
        companion = BatteryCompanion(cooldown_seconds=3600)
        self.assertTrue(companion.observe(BatteryStatus(19, False), now=0).announcement)
        companion.observe(BatteryStatus(23, False), now=20)
        self.assertFalse(companion.observe(BatteryStatus(18, False), now=30).announcement)
        self.assertTrue(companion.observe(BatteryStatus(19, False), now=4000).announcement)

    def test_desktop_without_battery_is_quiet(self):
        companion = BatteryCompanion()
        for now in (0, 90, 180):
            mood = companion.observe(None, now=now)
            self.assertEqual(mood.mode, "unavailable")
            self.assertFalse(mood.announcement)
            self.assertIsNone(public_battery(mood))
        self.assertEqual(
            public_battery(companion.observe(BatteryStatus(17, False), now=200)),
            {"percent": 17, "plugged": False, "mode": "low"},
        )

    def test_windows_api_valid_read(self):
        def get_power_status(pointer):
            native = pointer._obj
            native.ACLineStatus = 0
            native.BatteryFlag = 8
            native.BatteryLifePercent = 17
            return 1
        with patch("battery_life.sys.platform", "win32"), patch(
                "battery_life.ctypes.windll", create=True) as dll:
            dll.kernel32.GetSystemPowerStatus.side_effect = get_power_status
            self.assertEqual(read_battery(), BatteryStatus(17, False))

    def test_no_battery_or_unknown_sensor(self):
        for flag, ac, pct in ((128, 1, 100), (255, 0, 40),
                               (0, 255, 50), (0, 0, 255)):
            def sensor(pointer):
                native = pointer._obj
                native.ACLineStatus = ac
                native.BatteryFlag = flag
                native.BatteryLifePercent = pct
                return 1
            with self.subTest(flag=flag, ac=ac, pct=pct), patch(
                    "battery_life.sys.platform", "win32"), patch(
                    "battery_life.ctypes.windll", create=True) as dll:
                dll.kernel32.GetSystemPowerStatus.side_effect = sensor
                self.assertIsNone(read_battery())

    def test_non_windows_or_api_error(self):
        with patch("battery_life.sys.platform", "linux"):
            self.assertIsNone(read_battery())
        with patch("battery_life.sys.platform", "win32"), patch(
                "battery_life.ctypes.windll", create=True) as dll:
            dll.kernel32.GetSystemPowerStatus.return_value = 0
            self.assertIsNone(read_battery())


if __name__ == "__main__":
    unittest.main()
