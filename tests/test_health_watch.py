"""Verificação de saúde agregada, sem leitura de arquivos privados ou IA."""
import unittest
from unittest.mock import patch
from health_watch import HealthReading, HealthGuidance, read_health, summary


class HealthWatchTests(unittest.TestCase):
    def test_summary_distinguishes_values_from_unavailable(self):
        self.assertIn("indisponíveis", summary(None))
        text = summary(HealthReading(82, 11.4, 9.8))
        self.assertIn("82%", text)
        self.assertIn("11.4 GB", text)
        self.assertIn("não fecha", text)
        self.assertIn("indisponível", summary(HealthReading(None, None, None)))

    def test_high_ram_requires_two_consecutive_observations(self):
        watcher = HealthGuidance(cooldown_seconds=3600)
        high = HealthReading(94, 28.2, 20.0)
        self.assertEqual(watcher.observe(high, now=0), ())
        messages = watcher.observe(high, now=300)
        self.assertEqual(len(messages), 1)
        self.assertIn("RAM", messages[0])
        self.assertEqual(watcher.observe(high, now=600), ())
        self.assertEqual(watcher.observe(HealthReading(60, 28, 20), now=900), ())
        self.assertEqual(watcher.observe(high, now=1200), ())
        self.assertEqual(watcher.observe(high, now=4000), (messages[0],))

    def test_disk_pressure_is_separate_from_ram_and_resets(self):
        watcher = HealthGuidance()
        low_disk = HealthReading(45, 1.8, 2.7)
        self.assertFalse(watcher.observe(low_disk, now=0))
        msg = watcher.observe(low_disk, now=310)
        self.assertEqual(len(msg), 1)
        self.assertIn("espaço livre", msg[0])
        watcher.reset()
        self.assertFalse(watcher.observe(low_disk, now=400))
        self.assertFalse(watcher.observe(None, now=410))
        self.assertFalse(watcher.observe(low_disk, now=450))

    def test_no_os_reads_on_non_windows(self):
        with patch("health_watch.sys.platform", "linux"), patch(
                "health_watch.shutil.disk_usage") as disk:
            self.assertIsNone(read_health())
            disk.assert_not_called()

    def test_invalid_apis_do_not_invent_usage(self):
        with patch("health_watch.sys.platform", "win32"), patch(
                "health_watch.shutil.disk_usage", side_effect=OSError("indisponível")):
            self.assertIsNone(read_health())


if __name__ == "__main__":
    unittest.main()
