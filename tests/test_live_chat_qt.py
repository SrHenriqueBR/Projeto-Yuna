"""Chat formatado, cópia fiel, correção revisada e descarte de eventos Qt antigos."""
import importlib.util
import os
from threading import Thread
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
QT = importlib.util.find_spec("PySide6") is not None


@unittest.skipUnless(QT, "PySide6 não disponível")
class ChatWidgetsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_markdown_renders_and_code_copy_preserves_indentation(self):
        from chat_widgets import MessageCard
        code = 'def somar(a, b):\n    return a + b\n'
        original = "**Exemplo:**\n\n```python\n" + code + "```\n\nUse valores numéricos."
        card = MessageCard("Yuna", original)
        try:
            card.show()
            self.app.processEvents()
            self.assertNotIn("**Exemplo**", card.browser.toPlainText())
            self.assertIn("return a + b", card.browser.toPlainText())
            card.code_copy.click()
            self.assertEqual(self.app.clipboard().text(), code)
            card.copy.click()
            self.assertEqual(self.app.clipboard().text(), original)
            self.assertLessEqual(card.browser.height(), 460)
        finally:
            card.close()
            card.deleteLater()
            self.app.processEvents()

    def test_fences_require_matching_close_and_support_multiple_languages(self):
        from chat_widgets import code_blocks
        text = "```python\n    x = 1\n```\n~~~sql\nSELECT 1;\n~~~\n```js\nincompleto"
        self.assertEqual(code_blocks(text), [("python", "    x = 1\n"), ("sql", "SELECT 1;\n")])
        self.assertEqual(code_blocks("````python\n```\n````"), [("python", "```\n")])

    def test_resources_are_not_loaded_and_links_open_only_on_click(self):
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QTextDocument
        from chat_widgets import MessageCard
        with patch("chat_widgets.QDesktopServices.openUrl") as open_url:
            card = MessageCard("Yuna", '![foto](https://example.com/private.png)\n<img src="file:///private.png">\n[fonte](https://example.com/doc)')
            try:
                card.show()
                self.app.processEvents()
                open_url.assert_not_called()
                result = card.browser.document().resource(QTextDocument.ResourceType.ImageResource, QUrl("file:///private.png"))
                self.assertFalse(result)
                card.browser.anchorClicked.emit(QUrl("https://example.com/doc"))
                open_url.assert_called_once_with(QUrl("https://example.com/doc"))
                for url in ("javascript:alert(1)", "file:///private", "http://127.0.0.1/x", "http://localhost./x"):
                    card.browser.anchorClicked.emit(QUrl(url))
                self.assertEqual(open_url.call_count, 1)
            finally:
                card.close()
                card.deleteLater()
                self.app.processEvents()

    def test_user_html_is_displayed_as_literal_text(self):
        from chat_widgets import MessageCard
        original = '<b>não transformar</b><img src="file:///private">'
        card = MessageCard("Você", original)
        self.assertEqual(card.browser.toPlainText(), original)
        card.deleteLater()

    def test_preview_is_plain_transient_text(self):
        from chat_widgets import LiveAnswer
        preview = LiveAnswer()
        preview.update_text("<b>rascunho</b>")
        self.assertEqual(preview.text.toPlainText(), "<b>rascunho</b>")
        self.assertFalse(preview.isHidden())
        preview.clear()
        self.assertTrue(preview.isHidden())
        self.assertEqual(preview.text.toPlainText(), "")
        preview.deleteLater()


@unittest.skipUnless(QT, "PySide6 não disponível")
class LiveDesktopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        from yuna_desktop import YunaDesktop
        with patch("yuna_desktop.DesktopWorker.start"), \
             patch("compact_chat.QSystemTrayIcon.isSystemTrayAvailable", return_value=False):
            self.window = YunaDesktop()
        self.window.voice_index = 0

    def tearDown(self):
        self.window.companion.closing = True
        self.window.close()
        self.app.processEvents()

    def test_partial_mirrors_both_windows_without_becoming_message(self):
        window = self.window
        with patch.object(window, "add_message") as append, patch.object(window, "say") as speak:
            window.show_partial("Texto em progresso", window.worker._generation)
            self.assertEqual(window.reply_preview.text.toPlainText(), "Texto em progresso")
            self.assertEqual(window.companion.panel.reply_preview.text.toPlainText(), "Texto em progresso")
            append.assert_not_called()
            speak.assert_not_called()
            window.show_answer("Texto concluído", False, window.worker._generation)
            append.assert_called_once_with("Yuna", "Texto concluído", accent=False)
            self.assertTrue(window.reply_preview.isHidden())
            self.assertTrue(window.companion.panel.reply_preview.isHidden())

    def test_stop_rejects_already_queued_partial_final_error_and_status(self):
        window = self.window
        generation = window.worker._generation
        def emit_from_worker():
            window.signals.partial.emit("Rascunho antigo", generation)
            window.signals.replied.emit("Resposta antiga", False, generation)
            window.signals.taught.emit("Lição antiga", generation)
            window.signals.task_status.emit("Status antigo", generation)
            window.signals.task_error.emit("Erro antigo", generation)
        thread = Thread(target=emit_from_worker)
        thread.start()
        thread.join()
        window.emergency_stop()
        with patch.object(window, "add_message") as append, patch.object(window, "say") as speak:
            self.app.processEvents()
            append.assert_not_called()
            speak.assert_not_called()
        self.assertEqual(window.reply_preview.text.toPlainText(), "")
        self.assertNotEqual(window.status.text(), "Status antigo")
        window.show_partial("Nova resposta", window.worker._generation)
        self.assertEqual(window.reply_preview.text.toPlainText(), "Nova resposta")

    def test_failed_response_removes_preview(self):
        window = self.window
        generation = window.worker._generation
        window.show_partial("Parcial", generation)
        window.show_task_error("Ollama desconectou", generation)
        self.assertTrue(window.reply_preview.isHidden())
        self.assertTrue(window.composer.isEnabled())

    def test_correction_button_opens_unsaved_draft_for_that_question(self):
        from chat_widgets import MessageCard
        window = self.window
        window.add_message("Você", "Como estudar Python?")
        window.add_message("Yuna", "Resolva um exercício pequeno.")
        card = window.messages_container.findChildren(MessageCard)[-1]
        with patch("teaching_dialog.TeachingDialog") as dialog:
            card.teach.click()
        dialog.return_value.question.setText.assert_called_once_with("Como estudar Python?")
        dialog.return_value.answer.setPlainText.assert_called_once_with("Resolva um exercício pequeno.")
        dialog.return_value.save_lesson.assert_not_called()
        dialog.return_value.exec.assert_called_once()

    def test_compact_copy_uses_final_original_text_not_partial(self):
        panel = self.window.companion.panel
        original = "**Resposta**\n\n```python\nx = 1\n```"
        panel.add_message("Yuna", original)
        panel.reply_preview.update_text("Nova resposta incompleta")
        panel.copy_answer.click()
        self.assertEqual(self.app.clipboard().text(), original)


if __name__ == "__main__":
    unittest.main()
