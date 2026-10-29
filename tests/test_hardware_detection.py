import json
import subprocess
import unittest
from unittest.mock import patch

from hardware_detection import detect_hardware, detected_profile


class HardwareDetectionTests(unittest.TestCase):
    @patch("hardware_detection.sys.platform", "win32")
    @patch("hardware_detection.subprocess.run")
    def test_detects_ram_and_vram(self, run):
        run.return_value.stdout = json.dumps({"ram_gb": 16, "vram_gb": 8})
        self.assertEqual(detect_hardware(), {"ram_gb": 16, "vram_gb": 8})

    @patch("hardware_detection.sys.platform", "win32")
    @patch("hardware_detection.subprocess.run", side_effect=subprocess.TimeoutExpired("ps", 5))
    def test_timeout_is_safe(self, _run):
        self.assertIsNone(detect_hardware())

    @patch("hardware_detection.detect_hardware", return_value={"ram_gb": 16, "vram_gb": 8})
    def test_advanced_when_detected(self, _detect):
        self.assertEqual(detected_profile({}).name, "avancado")

    @patch("hardware_detection.detect_hardware", return_value=None)
    def test_light_when_unknown(self, _detect):
        self.assertEqual(detected_profile({}).name, "leve")

    @patch("hardware_detection.detect_hardware", return_value=None)
    def test_manual_override(self, _detect):
        self.assertEqual(detected_profile({"YUNA_PERFIL": "avancado"}).name, "avancado")
