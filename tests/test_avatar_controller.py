"""Regressões do contrato de eventos VTuber da Yuna."""
import unittest
from avatar_controller import AvatarController


class ControllerTests(unittest.TestCase):
    def test_audio_only_animates_after_real_start(self):
        c = AvatarController()
        self.assertFalse(c.dispatch("speech.level", sequence=1, speech_id="a", position_ms=1, amplitude=0.7))
        self.assertFalse(c.snapshot.speaking)
        self.assertTrue(c.dispatch("speech.started", sequence=2, speech_id="a"))
        self.assertTrue(c.dispatch("speech.level", sequence=3, speech_id="a", position_ms=10, amplitude=0.8))
        self.assertEqual(c.snapshot.mouth_level, 0.8)
        self.assertTrue(c.dispatch("speech.ended", sequence=4, speech_id="a"))
        self.assertEqual(c.snapshot.mouth_level, 0.0)
        self.assertFalse(c.snapshot.speaking)

    def test_cancel_blocks_old_audio(self):
        c = AvatarController()
        c.dispatch("speech.started", sequence=1, speech_id="old")
        c.dispatch("speech.interrupted", sequence=2, speech_id="old")
        c.dispatch("speech.started", sequence=3, speech_id="new")
        self.assertFalse(c.dispatch("speech.level", sequence=4, speech_id="old", position_ms=1, amplitude=1))
        self.assertFalse(c.dispatch("speech.level", sequence=2, speech_id="new", position_ms=1, amplitude=1))
        self.assertTrue(c.snapshot.speaking)
        self.assertEqual(c.snapshot.speech_id, "new")
        self.assertEqual(c.snapshot.mouth_level, 0.0)

    def test_invalid_inputs_do_not_mutate(self):
        c = AvatarController()
        for event, kwargs in [
            ("avatar.pose", {"pose": "delete_files"}),
            ("avatar.emotion", {"emotion": "happy", "intensity": float("nan")}),
            ("speech.started", {"speech_id": ""}),
            ("avatar.unknown", {}),
        ]:
            with self.assertRaises(ValueError):
                c.dispatch(event, sequence=1, **kwargs)
            self.assertEqual(c.snapshot.pose, "idle")
        self.assertTrue(c.dispatch("avatar.pose", sequence=1, pose="wave"))

    def test_old_positions_and_amplitude_are_rejected_or_clamped(self):
        c = AvatarController()
        c.dispatch("speech.started", sequence=1, speech_id="a")
        self.assertTrue(c.dispatch("speech.level", sequence=2, speech_id="a", position_ms=100, amplitude=5))
        self.assertEqual(c.snapshot.mouth_level, 1.0)
        self.assertFalse(c.dispatch("speech.level", sequence=3, speech_id="a", position_ms=99, amplitude=0.1))
        self.assertEqual(c.snapshot.position_ms, 100)
        self.assertTrue(c.dispatch("speech.level", sequence=4, speech_id="a", position_ms=101, amplitude=-2))
        self.assertEqual(c.snapshot.mouth_level, 0.0)


if __name__ == "__main__":
    unittest.main()
