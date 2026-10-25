"""Contrato mínimo do UI de consentimento sem depender do Qt no CI."""
import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ConsentTests(unittest.TestCase):
    def setUp(self):
        self.code = (ROOT / "yuna_overlay.py").read_text(encoding="utf-8")
        self.module = ast.parse(self.code)

    def get_method(self, name):
        cls = next(n for n in self.module.body
                   if isinstance(n, ast.ClassDef) and n.name == "YunaOverlay")
        return next(n for n in cls.body
                    if isinstance(n, ast.FunctionDef) and n.name == name)

    def test_consent_is_inline_without_modal_window(self):
        method = self.get_method("cycle_voice")
        code = ast.get_source_segment(self.code, method)
        self.assertNotIn("QMessageBox", self.code)
        self.assertIn("voice_confirm_pending", code)
        self.assertIn('self.voice_engine = "edge"', code)
        self.assertIn("self.cancel_voice_button.show()", code)
        self.assertIn("self.say(", code)

    def test_user_can_cancel_before_any_online_voice_is_active(self):
        code = ast.get_source_segment(self.code, self.get_method("cancel_voice_consent"))
        self.assertIn("voice_confirm_pending = False", code)
        self.assertIn("cancel_voice_button.hide()", code)
        self.assertNotIn('voice_engine = "edge"', code)

    def test_close_does_not_rely_on_qt_tool_lifecycle(self):
        self.assertIn("app.setQuitOnLastWindowClosed(False)", self.code)
        close = ast.get_source_segment(self.code, self.get_method("closeEvent"))
        self.assertIn("QApplication.quit", close)


if __name__ == "__main__":
    unittest.main()
