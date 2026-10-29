import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@unittest.skipUnless(importlib.util.find_spec("PySide6"), "PySide6 indisponível")
class PosePriorityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_curious_pose_is_visible(self):
        from yuna_avatar import YunaAvatar
        with tempfile.TemporaryDirectory() as root:
            avatar = YunaAvatar(Path(root))
            try:
                avatar.animation.stop()
                avatar.set_pose("curious", seconds=10)
                self.assertEqual(avatar.visible_pose(), "curious")
                avatar.set_speaking(True)
                self.assertEqual(avatar.visible_pose(), "curious")
            finally:
                avatar.close()

    def test_wave_does_not_disappear_during_speech(self):
        from yuna_avatar import YunaAvatar
        with tempfile.TemporaryDirectory() as root:
            avatar = YunaAvatar(Path(root))
            try:
                avatar.animation.stop()
                avatar.set_pose("wave", seconds=10)
                avatar.set_speaking(True)
                self.assertEqual(avatar.visible_pose(), "wave")
            finally:
                avatar.close()
