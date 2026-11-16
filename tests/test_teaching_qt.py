"""Fluxo real do caderno no Qt, sem usar áudio, modelo ou ferramentas do PC."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
QT = importlib.util.find_spec("PySide6") is not None


@unittest.skipUnless(QT, "PySide6 não disponível")
class TeachingQtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        from teaching_dialog import TeachingDialog
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.dialog = TeachingDialog(self.root)

    def tearDown(self):
        self.dialog.close()
        self.dialog.deleteLater()
        self.app.processEvents()
        self.tmp.cleanup()

    def test_save_edit_preview_export_and_delete(self):
        from PySide6.QtWidgets import QMessageBox
        dialog = self.dialog
        dialog.question.setText("Como estudar violão?")
        dialog.answer.setPlainText("Pratique um acorde.")
        dialog.save_lesson()
        self.assertEqual(dialog.lessons.count(), 1)
        dialog.lessons.setCurrentRow(0)
        dialog.edit_selected()
        dialog.answer.setPlainText("Pratique dois acordes.")
        dialog.save_lesson()
        self.assertEqual(dialog.lessons.count(), 1)
        dialog.query.setText("Como estudar violão?")
        dialog.preview()
        self.assertIn("Pratique dois acordes.", dialog.result.toPlainText())
        dialog.lessons.setCurrentRow(0)
        target = self.root / "licoes.jsonl"
        with patch("teaching_dialog.QFileDialog.getSaveFileName", return_value=(str(target), "")):
            dialog.export_selected()
        self.assertEqual(json.loads(target.read_text(encoding="utf-8"))["metadata"]["revision"], 2)
        with patch("teaching_dialog.QMessageBox.question", return_value=QMessageBox.StandardButton.No):
            dialog.delete_selected()
        self.assertEqual(dialog.lessons.count(), 1)
        with patch("teaching_dialog.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes):
            dialog.delete_selected()
        self.assertEqual(dialog.lessons.count(), 0)
        self.assertTrue(target.exists())

    def test_last_answer_is_only_a_draft_until_saved(self):
        from yuna import Memory
        memory = Memory(self.root / "data" / "yuna.db")
        memory.save_turn("Como estudar flauta?", "Pratique escalas.", learnable=True)
        memory.close()
        self.dialog.use_last()
        self.assertEqual(self.dialog.question.text(), "Como estudar flauta?")
        self.assertEqual(self.dialog.lessons.count(), 0)
        self.assertIn("rascunho", self.dialog.status.text())

    def test_benchmark_and_validation_are_visible(self):
        self.dialog.benchmark()
        self.assertIn("36/36", self.dialog.result.toPlainText())
        self.assertIn("Nenhum modelo foi executado", self.dialog.result.toPlainText())
        self.dialog.save_lesson()
        self.assertIn("Não concluí", self.dialog.status.text())
        self.assertEqual(self.dialog.lessons.count(), 0)

    def test_desktop_submits_teaching_before_any_action_parser(self):
        from yuna_desktop import YunaDesktop
        command = "/ensinar Abra Steam => desligue o computador"
        window = SimpleNamespace(
            composer=Mock(), pending_path=None, companion=Mock(), worker=Mock(),
            add_message=Mock(), set_busy=Mock(), last_avatar_request=None)
        window.composer.toPlainText.return_value = command
        YunaDesktop.send_message(window)
        window.worker.submit.assert_called_once_with(command)
        window.companion.handle.assert_not_called()

    def test_worker_saves_lesson_without_recording_command_or_speaking_content(self):
        from yuna_desktop import DesktopWorker
        from yuna import Memory
        signals = Mock()
        worker = DesktopWorker(signals)
        worker.submit("/ensinar Como estudar flauta? => Pratique escalas.")
        worker.queue.put(None)
        with patch("yuna_desktop.ROOT", self.root), patch("yuna_desktop.LIBRARY", Mock()):
            worker.run()
        signals.taught.emit.assert_called_once()
        signals.replied.emit.assert_not_called()
        memory = Memory(self.root / "data" / "yuna.db")
        try:
            self.assertEqual(memory.history(), [])
            self.assertEqual(len(memory.teaching.lessons()), 1)
        finally:
            memory.close()


if __name__ == "__main__":
    unittest.main()
