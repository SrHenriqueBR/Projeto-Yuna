"""Valida ponte local Python/Unreal sem Unreal instalado e sem rede."""
import json
from pathlib import Path
import tempfile
import unittest

from avatar_controller import AvatarController
from unreal_state_bridge import UnrealStateBridge


class UnrealBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.now = [1_800_000_000.0, 10.0]
        self.bridge = UnrealStateBridge(
            self.root, clock=lambda: self.now[0],
            monotonic=lambda: self.now[1])
        self.controller = AvatarController()
        self.sequence = 0

    def tearDown(self):
        self.bridge.stop()
        self.temp.cleanup()

    def event(self, name, **kwargs):
        self.sequence += 1
        self.assertTrue(self.controller.dispatch(name, sequence=self.sequence, **kwargs))
        return self.controller.snapshot

    def read(self):
        return json.loads(self.bridge.path.read_text(encoding="utf-8"))

    def test_off_by_default_and_no_network(self):
        self.assertFalse(self.bridge.enabled)
        self.assertFalse(self.bridge.publish(self.controller.snapshot))
        self.assertFalse(self.bridge.path.exists())
        self.assertTrue((Path(__file__).parents[1] / "unreal" / "YunaUnreal"
                         / "YunaUnreal.uproject").is_file())

    def test_only_animation_fields_are_exposed(self):
        self.bridge.start(self.controller.snapshot)
        initial = self.read()
        self.assertEqual(initial["version"], 1)
        self.assertEqual(initial["pose"], "idle")
        self.assertFalse(initial["speaking"])
        self.assertEqual(initial["updated_at"], self.now[0])
        self.assertEqual(
            set(initial), {"version", "session", "updated_at", "revision",
                           "gesture_seq", "pose", "emotion", "intensity",
                           "speaking", "has_amplitude", "mouth_level"})
        self.assertNotIn("conversation", self.bridge.path.read_text())
        self.assertFalse(list(self.bridge.path.parent.glob(".yuna_unreal_*.tmp")))

    def test_pose_emotion_and_live_voice_level(self):
        self.bridge.start(self.controller.snapshot)
        snap = self.event("avatar.pose", pose="wave")
        self.assertTrue(self.bridge.publish(snap, event="avatar.pose"))
        self.assertEqual(self.read()["pose"], "wave")
        snap = self.event("avatar.emotion", emotion="happy", intensity=0.7)
        self.assertTrue(self.bridge.publish(snap, event="avatar.emotion"))
        self.assertEqual(self.read()["emotion"], "happy")
        self.assertAlmostEqual(self.read()["intensity"], 0.7)
        self.assertGreaterEqual(self.read()["gesture_seq"], 2)
        snap = self.event("speech.started", speech_id="a1")
        self.bridge.publish(snap, event="speech.started")
        snap = self.event("speech.level", speech_id="a1", position_ms=100, amplitude=0.8)
        self.assertTrue(self.bridge.publish(snap, event="speech.level",
                                            has_amplitude=True))
        self.assertAlmostEqual(self.read()["mouth_level"], 0.8)
        self.assertTrue(self.read()["has_amplitude"])
        self.now[1] += 0.02
        snap = self.event("speech.level", speech_id="a1", position_ms=120, amplitude=0.7)
        self.assertFalse(self.bridge.publish(snap, event="speech.level"))
        self.assertAlmostEqual(self.read()["mouth_level"], 0.8)
        self.now[1] += 0.12
        snap = self.event("speech.level", speech_id="a1", position_ms=250, amplitude=0.3)
        self.assertTrue(self.bridge.publish(snap, event="speech.level"))
        self.assertAlmostEqual(self.read()["mouth_level"], 0.3)
        snap = self.event("speech.ended", speech_id="a1")
        self.bridge.publish(snap, event="speech.ended")
        self.assertFalse(self.read()["speaking"])
        self.assertFalse(self.read()["has_amplitude"])
        self.assertEqual(self.read()["mouth_level"], 0.0)

    def test_file_cleared_on_stop_without_deleting_other_session(self):
        self.bridge.start(self.controller.snapshot)
        self.bridge.stop()
        self.assertFalse(self.bridge.path.exists())
        self.bridge.start(self.controller.snapshot)
        data = self.read()
        data["session"] = "another-session"
        self.bridge.path.write_text(json.dumps(data), encoding="utf-8")
        self.bridge.stop()
        self.assertTrue(self.bridge.path.exists())

    def test_invalid_input_remains_whitelisted(self):
        from types import SimpleNamespace
        self.bridge.start(self.controller.snapshot)
        fake = SimpleNamespace(
            pose="delete_system", emotion="admin", speaking=True,
            mouth_level=float("nan"), intensity=float("inf"),
            private_message="password", api_key="secret")
        self.assertTrue(self.bridge.publish(fake, event="avatar.pose"))
        data = self.read()
        self.assertEqual(data["pose"], "idle")
        self.assertEqual(data["emotion"], "neutral")
        self.assertEqual(data["mouth_level"], 0.0)
        self.assertEqual(data["intensity"], 0.0)
        self.assertNotIn("api_key", data)
        self.assertNotIn("private_message", data)


if __name__ == "__main__":
    unittest.main()
