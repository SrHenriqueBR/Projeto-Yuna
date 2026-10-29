"""Yuna 0.24: caminho natural, olhar suave e acessibilidade local."""
import importlib.util
import math
import os
import tempfile
from pathlib import Path
from unittest.mock import patch
import unittest

import avatar_state
from avatar_motion import ambient_pose, ease_gaze, frame_at
import yuna

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class AmbientMotionTests(unittest.TestCase):
    def test_ambient_cycle_has_walk_pause_and_rest(self):
        self.assertEqual(ambient_pose(0), "walk")
        self.assertEqual(ambient_pose(314), "walk")
        self.assertEqual(ambient_pose(315), "idle")
        self.assertEqual(ambient_pose(395), "walk")
        self.assertEqual(ambient_pose(585), "sit")
        self.assertEqual(ambient_pose(755), "idle")
        self.assertEqual(ambient_pose(900), "walk")
        self.assertEqual(ambient_pose(120, walking=False), "idle")
        self.assertEqual(ambient_pose(120, reduced_motion=True), "idle")
        self.assertEqual(ambient_pose(620, reduced_motion=True), "idle")

    def test_eased_gaze_moves_gradually_and_returns_to_center(self):
        centered = (95.0, 135.0)
        target = (185.0, 160.0)
        first = ease_gaze(centered, target)
        self.assertGreater(first[0], centered[0])
        self.assertLess(first[0], target[0])
        second = ease_gaze(first, target)
        self.assertGreater(second[0], first[0])
        self.assertLess(second[0], target[0])
        reset = ease_gaze(second, centered)
        self.assertLess(reset[0], second[0])
        self.assertEqual(ease_gaze(centered, target, strength=0), centered)
        self.assertEqual(ease_gaze(centered, target, strength=5), target)

    def test_motion_math_is_finite_at_many_ticks_and_poses(self):
        for tick in (0, 100, 900, 100000):
            for pose in ("walk", "sit", "idle", "talk", "sleepy", "laugh"):
                with self.subTest(tick=tick, pose=pose):
                    frame = frame_at(tick, pose)
                    self.assertTrue(math.isfinite(frame.hair_sway))
                    self.assertTrue(math.isfinite(frame.body_bob))
                    self.assertTrue(math.isfinite(frame.tilt))


class ReducedMotionTests(unittest.TestCase):
    def test_old_preferences_migrate_and_extra_input_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            avatar_state.save_style(root, {
                "hair": "branco", "eyes": "azuis", "size": "grande",
                "walking": True,
            })
            state = avatar_state.load_style(root)
            self.assertFalse(state["reduced_motion"])
            self.assertEqual(state["size"], "grande")
            self.assertFalse(avatar_state.validated(
                {"reduced_motion": "False"})["reduced_motion"])
            self.assertTrue(avatar_state.validated(
                {"reduced_motion": True})["reduced_motion"])

    def test_local_commands_are_precise_and_persist(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with patch.object(yuna, "ROOT", root):
                memory = yuna.Memory(root / "data" / "yuna.db")
                try:
                    requests = (
                        ("Yuna, reduza as animações", True),
                        ("Yuna retoma as animações", False),
                        ("Yuna ativa movimento reduzido", True),
                    )
                    for phrase, desired in requests:
                        with self.subTest(phrase=phrase):
                            self.assertEqual(
                                avatar_state.parse_avatar_request(phrase),
                                ("motion", desired))
                            with patch("yuna.ask_model",
                                       side_effect=AssertionError("Ollama não é necessário")):
                                self.assertTrue(yuna.handle_message(memory, phrase))
                            self.assertEqual(
                                avatar_state.load_style(root)["reduced_motion"],
                                desired)
                    self.assertEqual(len(memory.history()), 6)
                finally:
                    memory.close()

    def test_hypothetical_or_mixed_request_is_not_a_toggle(self):
        for phrase in (
            "Como reduzir as animações?",
            "Yuna não reduza as animações",
            "Yuna, talvez reduza as animações",
            "Se eu pedir para reduzir as animações, funciona?",
            "Yuna, reduza as animações e delete arquivos",
        ):
            with self.subTest(phrase=phrase):
                self.assertIsNone(avatar_state.parse_avatar_request(phrase))

    def test_reduced_motion_preserves_eye_position_but_not_animation(self):
        frame = frame_at(27, "walk", cursor=(280, 270),
                         speaking=True, reduced_motion=True)
        self.assertGreater(frame.eye_dx, 0)
        self.assertEqual(frame.hair_sway, 0)
        self.assertEqual(frame.body_bob, 0)
        self.assertEqual(frame.mouth_open, 0)


@unittest.skipUnless(importlib.util.find_spec("PySide6"), "Qt opcional")
class AmbientQtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_widget_respects_reduced_motion_and_does_not_shift_windows(self):
        from yuna_avatar import YunaAvatar
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            avatar_state.save_style(root, {
                "reduced_motion": True,
                "walking": True, "size": "grande",
            })
            avatar = YunaAvatar(root)
            try:
                avatar.show()
                self.app.processEvents()
                start = avatar.pos()
                self.assertEqual(avatar.visible_pose(), "idle")
                for _ in range(5):
                    avatar.advance()
                self.assertEqual(avatar.pos(), start)
                self.assertEqual(avatar.visible_pose(), "idle")
                self.assertEqual(avatar.width(), round(190 * 1.30))
                avatar.set_pose("wink", 2)
                self.app.processEvents()
                self.assertEqual(avatar.visible_pose(), "wink")
                self.assertFalse(avatar.grab().toImage().isNull())
                avatar.hide()
                old_ticks = avatar.tick_count
                avatar.advance()
                self.assertEqual(avatar.tick_count, old_ticks)
            finally:
                avatar.close()

    def test_widget_eases_cursor_target(self):
        from yuna_avatar import YunaAvatar
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            avatar_state.save_style(root, {"walking": False})
            avatar = YunaAvatar(root)
            try:
                avatar.show()
                self.app.processEvents()
                from PySide6.QtCore import QPoint
                # Não substituir a classe Qt nativa QCursor por MagicMock:
                # isso pode provocar falhas no runner Windows/PySide6.
                avatar._update_gaze(avatar.mapToGlobal(QPoint(170, 210)))
                self.assertGreater(avatar._eye_cursor[0], 95)
                self.assertLess(avatar._eye_cursor[0], 170)
            finally:
                avatar.close()


if __name__ == "__main__":
    unittest.main()
