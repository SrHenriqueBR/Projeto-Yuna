import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@unittest.skipUnless(importlib.util.find_spec("PySide6"), "PySide6 indisponível")
class AvatarFpsProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_light_and_advanced_timer(self):
        from yuna_avatar import YunaAvatar
        with tempfile.TemporaryDirectory() as root:
            with patch.dict(os.environ, {"YUNA_PERFIL": "leve"}):
                avatar = YunaAvatar(Path(root))
            try:
                avatar.animation.stop()
                self.assertEqual(avatar.animation.interval(), 83)
                with patch.dict(os.environ, {"YUNA_PERFIL": "avancado"}):
                    avatar.refresh_animation_profile()
                self.assertEqual(avatar.animation.interval(), 33)
            finally:
                avatar.close()
