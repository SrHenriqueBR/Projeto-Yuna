"""Yuna 0.25: voz audível e animação ligada ao áudio reproduzido."""
from array import array
import importlib.util
import math
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave

import voice
from avatar_motion import frame_at

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def make_wav(path):
    sample_rate = 16000
    with wave.open(str(path), "wb") as sound:
        sound.setnchannels(1)
        sound.setsampwidth(2)
        sound.setframerate(sample_rate)
        samples = array("h")
        samples.extend([0] * 1600)
        samples.extend(int(9000 * math.sin(2 * math.pi * 250 * t / sample_rate))
                       for t in range(3200))
        if sys.byteorder != "little":
            samples.byteswap()
        sound.writeframes(samples.tobytes())


class VoiceWaveTests(unittest.TestCase):
    def test_wave_envelope_captures_silence_then_audible_voice(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "teste.wav"
            make_wav(path)
            levels = voice.wave_envelope(path)
            self.assertGreaterEqual(len(levels), 6)
            self.assertEqual(voice.mouth_level_at(levels, 0), 0.0)
            self.assertGreater(voice.mouth_level_at(levels, 190), 0.3)
            self.assertEqual(voice.mouth_level_at(levels, 100000), 0.0)
            self.assertIsNone(voice.mouth_level_at([], 100))
            self.assertIsNone(voice.mouth_level_at(levels, -1))

    def test_wave_without_valid_audio_falls_back_safely(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad.wav"
            path.write_bytes(b"not a wav")
            self.assertEqual(voice.wave_envelope(path), [])

    def test_windows_script_is_local_and_uses_environment_for_output(self):
        script = voice.WINDOWS_WAV_SCRIPT
        self.assertIn("SetOutputToWaveFile", script)
        self.assertIn("YUNA_LOCAL_WAV_PATH", script)
        self.assertIn("[Console]::In.ReadToEnd()", script)
        self.assertIn("Gender -eq 'Female'", script)
        self.assertNotIn("http", script.lower())

    @unittest.skipUnless(os.name == "nt", "Geração WAV local requer Windows")
    def test_generate_windows_file_uses_safe_subprocess(self):
        class Success:
            returncode = 0
            stderr = ""

        def fake_run(*args, **kwargs):
            self.assertFalse(kwargs["shell"])
            self.assertIn("Oi, Kaizen!", kwargs["input"])
            self.assertTrue(kwargs["env"]["YUNA_LOCAL_WAV_PATH"].endswith(".wav"))
            make_wav(kwargs["env"]["YUNA_LOCAL_WAV_PATH"])
            return Success()

        with patch("voice.subprocess.run", side_effect=fake_run):
            result = voice.synthesize_windows("Oi, **Kaizen**!")
        try:
            self.assertEqual(result.suffix, ".wav")
            self.assertTrue(result.exists())
            self.assertGreater(len(voice.wave_envelope(result)), 3)
        finally:
            result.unlink(missing_ok=True)

    def test_mouth_level_drives_motion_not_just_the_timer(self):
        quiet = frame_at(23, "talk", speaking=True, mouth_level=0.0)
        loud = frame_at(23, "talk", speaking=True, mouth_level=1.0)
        self.assertEqual(quiet.mouth_open, 0.0)
        self.assertEqual(loud.mouth_open, 6.0)
        self.assertEqual(frame_at(23, "idle", speaking=False,
                                  mouth_level=1.0).mouth_open, 0.0)
        self.assertGreater(frame_at(23, "idle", speaking=True).mouth_open, 0.0)


@unittest.skipUnless(importlib.util.find_spec("PySide6"), "Qt opcional")
class VoiceDesktopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_desktop_defaults_to_offline_and_has_a_test_button(self):
        from yuna_desktop import YunaDesktop
        with patch("yuna_desktop.DesktopWorker.start"):
            window = YunaDesktop()
        try:
            self.assertEqual(window.voice_index, 1)
            self.assertEqual(window.voice_selector.currentIndex(), 1)
            self.assertIn("Testar voz", window.voice_test.text())
            self.assertFalse(window.voice_busy)
            with patch("yuna_desktop.Thread") as fake_thread:
                window.test_voice()
                fake_thread.return_value.start.assert_called_once()
            self.assertIsNotNone(window.avatar_window)
            self.assertFalse(window.avatar_window.speaking)
            self.assertTrue(window.voice_busy)
            from PySide6.QtMultimedia import QMediaPlayer
            window.playback_state_changed(QMediaPlayer.PlaybackState.PlayingState)
            self.assertTrue(window.avatar_window.speaking)
            window.avatar_window.set_mouth_level(.7)
            self.assertEqual(window.avatar_window.mouth_level, .7)
            window.playback_state_changed(QMediaPlayer.PlaybackState.StoppedState)
            self.assertFalse(window.avatar_window.speaking)
            self.assertIsNone(window.avatar_window.mouth_level)
            window.voice_error("Voz não instalada")
            self.assertFalse(window.voice_busy)
            self.assertIn("Voz indisponível", window.status.text())
        finally:
            window.close()
            self.app.processEvents()

    def test_disabled_voice_does_not_start_mouth_or_work(self):
        from yuna_desktop import YunaDesktop
        with patch("yuna_desktop.DesktopWorker.start"):
            window = YunaDesktop()
        try:
            window.voice_index = 0
            with patch("yuna_desktop.Thread") as fake_thread:
                window.say("Olá!")
                fake_thread.assert_not_called()
            self.assertFalse(window.voice_busy)
        finally:
            window.close()


if __name__ == "__main__":
    unittest.main()
