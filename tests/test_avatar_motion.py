"""Yuna 0.20: movement, expression and speech-sync regressions."""
import importlib.util
import math
import os
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from avatar_motion import frame_at

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
QT = importlib.util.find_spec("PySide6") is not None


class MotionTests(unittest.TestCase):
    def test_blinks_periodically_without_external_input(self):
        self.assertEqual(frame_at(1, "idle").blink, 1.0)
        self.assertEqual(frame_at(2, "idle").blink, 1.0)
        self.assertEqual(frame_at(3, "idle").blink, 0.0)
        self.assertEqual(frame_at(61, "idle").blink, 1.0)
        self.assertEqual(frame_at(128, "idle").blink, 1.0)

    def test_cursor_tracking_is_bounded(self):
        frame = frame_at(15, "idle", cursor=(20000, -20000))
        self.assertEqual(frame.eye_dx, 3.0)
        self.assertEqual(frame.eye_dy, -2.0)
        centered = frame_at(15, "idle", cursor=(95, 135))
        self.assertEqual(centered.eye_dx, 0)
        self.assertEqual(centered.eye_dy, 0)

    def test_speaking_animation_is_nonzero_and_silent_is_zero(self):
        self.assertEqual(frame_at(10, "idle", speaking=False).mouth_open, 0.0)
        self.assertGreater(frame_at(10, "idle", speaking=True).mouth_open, 0.0)
        self.assertGreater(frame_at(11, "talk").mouth_open, 0.0)

    def test_walk_and_idle_animation_have_distinct_movement(self):
        walk = frame_at(29, "walk")
        idle = frame_at(29, "idle")
        self.assertGreater(abs(walk.body_bob), abs(idle.body_bob))
        self.assertLessEqual(abs(walk.hair_sway), 5)
        self.assertTrue(math.isfinite(walk.breath))

    def test_optional_reduced_motion_stops_oscillation(self):
        state = frame_at(7, "talk", cursor=(999, 0),
                         speaking=True, reduced_motion=True)
        self.assertEqual(state.hair_sway, 0)
        self.assertEqual(state.breath, 0)
        self.assertEqual(state.body_bob, 0)
        self.assertEqual(state.mouth_open, 0)
        self.assertNotEqual(state.eye_dx, 0)


@unittest.skipUnless(QT, "PySide6 não instalado neste ambiente")
class AvatarVisualTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_renders_all_poses_and_hair_colors(self):
        from yuna_avatar import YunaAvatar
        from avatar_state import save_style
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            avatar = YunaAvatar(root)
            try:
                avatar.show()
                self.app.processEvents()
                for hair in ("preto", "branco", "ruivo", "roxo"):
                    save_style(root, {
                        "hair": hair, "eyes": "vermelhos",
                        "outfit": "escura", "walking": False,
                    })
                    avatar.reload_appearance()
                    for pose in ("idle", "sit", "angry", "happy", "talk"):
                        avatar.set_pose(pose, seconds=5)
                        avatar.tick_count += 3
                        self.app.processEvents()
                        image = avatar.grab().toImage()
                        self.assertFalse(image.isNull())
                        self.assertEqual(image.width(), avatar.width())
                        self.assertGreater(image.pixelColor(95, 135).alpha(), 0)
                avatar.set_speaking(True)
                self.assertEqual(avatar.visible_pose(), "talk")
                avatar.set_speaking(False)
                self.assertNotEqual(avatar.visible_pose(), "talk")
            finally:
                avatar.close()

    def test_speech_cycle_from_desktop_changes_avatar_state(self):
        from yuna_desktop import YunaDesktop
        with patch("yuna_desktop.DesktopWorker.start"):
            window = YunaDesktop()
        try:
            window.show()
            window.toggle_avatar()
            self.app.processEvents()
            self.assertTrue(window.avatar_window.isVisible())
            window.voice_index = 0  # Não animar lábios sem áudio.
            window.show_answer("Uma resposta de teste.", False)
            self.assertFalse(window.avatar_window.speaking)
            window.voice_index = 1  # Windows offline TTS
            with patch("yuna_desktop.Thread") as thread:
                window.say("Teste de sincronização.")
                thread.return_value.start.assert_called_once()
            self.assertFalse(window.avatar_window.speaking)
            from PySide6.QtMultimedia import QMediaPlayer
            window.playback_state_changed(QMediaPlayer.PlaybackState.PlayingState)
            self.assertTrue(window.avatar_window.speaking)
            window.voice_error("")
            self.assertFalse(window.avatar_window.speaking)
            window.toggle_avatar()
            self.assertFalse(window.avatar_window.isVisible())
        finally:
            window.close()
            self.app.processEvents()


if __name__ == "__main__":
    unittest.main()
