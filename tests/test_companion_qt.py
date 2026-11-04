"""Fluxos reais Qt, sem usar áudio, câmera, teclado ou desligamento do host."""
import importlib.util
from contextlib import closing
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@unittest.skipUnless(importlib.util.find_spec("PySide6"), "Qt opcional")
class CompanionQtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        from yuna_desktop import YunaDesktop
        with patch("yuna_desktop.DesktopWorker.start"), patch(
                "compact_chat.QSystemTrayIcon.isSystemTrayAvailable", return_value=False):
            self.window = YunaDesktop()
        self.window.voice_index = 0
        self.controller = self.window.companion

    def tearDown(self):
        self.controller.closing = True
        self.window.close()
        self.app.processEvents()

    def test_small_window_mirrors_messages_and_routes_to_same_worker(self):
        self.controller.show_compact()
        self.window.add_message("Você", "<script>texto</script>")
        self.app.processEvents()
        self.assertFalse(self.window.isVisible())
        self.assertTrue(self.controller.panel.isVisible())
        self.assertLess(self.controller.panel.width(), 600)
        self.assertIn("<script>texto</script>", self.controller.panel.messages.toPlainText())
        with patch.object(self.window.worker, "submit") as submit:
            self.controller.panel.input.setPlainText("Converse comigo")
            self.controller.panel.submit()
            submit.assert_called_once_with("Converse comigo")

    def test_audio_disconnection_opens_once_and_reconnection_rearms(self):
        with patch("compact_chat.QMediaDevices.audioInputs", return_value=[]), patch.object(
                self.controller, "show_compact") as show:
            self.controller.check_audio()
            self.controller.check_audio()
            show.assert_called_once()
        device = Mock()
        device.isNull.return_value = False
        with patch("compact_chat.QMediaDevices.audioInputs", return_value=[device]), patch(
                "compact_chat.QMediaDevices.audioOutputs", return_value=[device]), patch(
                "compact_chat.QMediaDevices.defaultAudioInput", return_value=device), patch(
                "compact_chat.QMediaDevices.defaultAudioOutput", return_value=device), patch(
                "compact_chat.importlib.util.find_spec", return_value=True), patch.object(
                self.window.audio_output, "setDevice"):
            self.controller.check_audio()
            self.assertFalse(self.controller.audio_missing)
        with patch("compact_chat.QMediaDevices.audioInputs", return_value=[]), patch.object(
                self.controller, "show_compact") as show:
            self.controller.check_audio()
            show.assert_called_once()

    def test_tray_close_keeps_worker_and_explicit_exit_cleans_up(self):
        self.controller.tray_available = True
        self.window.show()
        with patch.object(self.window.worker, "stop") as stop:
            self.window.close()
            stop.assert_not_called()
            self.assertFalse(self.window.isVisible())
            self.controller.closing = True
            self.window.close()
            stop.assert_called_once()

    def test_stop_cancels_shutdown_game_and_late_wake(self):
        self.controller.shutdown.start()
        self.window.game_session.authorize(r"C:\Games\Demo\game.exe", approved=True, single_player=True)
        generation = self.controller.wake_generation
        self.controller.wake = Mock()
        self.controller.wake_action.blockSignals(True)
        self.controller.wake_action.setChecked(True)
        self.controller.wake_action.blockSignals(False)
        with patch.object(self.controller, "submit") as submit:
            self.window.emergency_stop()
            self.controller._heard(generation, "Yuna desliga o computador")
            submit.assert_not_called()
        self.assertIsNone(self.controller.shutdown.remaining())
        self.assertFalse(self.window.game_session.active)

    def test_cancellation_works_while_busy_and_does_not_call_model(self):
        self.controller.shutdown.start()
        self.window.set_busy(True)
        with patch.object(self.window.worker, "submit") as model:
            self.controller.submit("Yuna cancele o desligamento")
            model.assert_not_called()
        self.assertIsNone(self.controller.shutdown.remaining())

    def test_attachment_never_intercepts_shutdown_cancel(self):
        self.controller.shutdown.start()
        self.window.pending_path = Path("documento.pdf")
        self.window.set_busy(True)
        with patch.object(self.window.worker, "analyze") as analyze:
            self.controller.submit("Yuna cancele o desligamento")
            analyze.assert_not_called()
        self.assertIsNone(self.controller.shutdown.remaining())

    def test_dictation_preserves_compact_draft_and_stop_ignores_late_transcript(self):
        self.controller.show_compact()
        self.controller.panel.input.setPlainText("rascunho")
        self.window.microphone_ready("continuação")
        self.assertEqual(self.controller.panel.input.toPlainText(), "rascunho\ncontinuação")
        generation = self.window._mic_generation
        self.window.emergency_stop()
        self.window.microphone_ready("fala antiga", generation)
        self.assertEqual(self.controller.panel.input.toPlainText(), "rascunho\ncontinuação")

    def test_scheduled_wake_denial_enqueues_nothing(self):
        from PySide6.QtWidgets import QMessageBox
        with patch("compact_chat.QMessageBox.question", return_value=QMessageBox.StandardButton.No), patch.object(
                self.window.worker.queue, "put") as queue:
            self.controller.handle("Yuna acorde o computador amanhã às 07:00")
            queue.assert_not_called()

    def test_stop_discards_queued_game_timer_before_any_input(self):
        self.window.game_session.authorize(r"C:\Games\Demo\game.exe", approved=True, single_player=True)
        pending = []
        with patch("compact_chat.QTimer.singleShot", side_effect=lambda _, fn: pending.append(fn)), patch(
                "compact_chat.Thread") as thread:
            self.controller.queue_game("Yuna no jogo pule", "jump")
            self.controller.stop_game()
            pending[-1]()
            thread.assert_not_called()

    def test_stopped_speech_file_is_discarded_without_playback(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "voice.wav"
            path.write_bytes(b"not played")
            self.window.emergency_stop()
            with patch.object(self.window.player, "play") as play:
                self.window.play_audio(str(path))
                play.assert_not_called()
                self.assertFalse(path.exists())

    def test_old_audio_cannot_play_after_a_new_response(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "old.wav"
            path.write_bytes(b"old speech")
            generation = self.window._speech_generation
            self.window._speech_generation += 1
            self.window._stop_requested = False
            with patch.object(self.window.player, "play") as play:
                self.window.play_audio(str(path), generation)
                play.assert_not_called()
                self.assertFalse(path.exists())

    @unittest.skipUnless(os.name == "nt", "IPC real verificado no Windows")
    def test_second_instance_only_activates_existing_window(self):
        from compact_chat import SingleInstance
        first, second = SingleInstance(), SingleInstance()
        activated = Mock()
        first.activated.connect(activated)
        try:
            self.assertTrue(first.acquire())
            self.assertFalse(second.acquire())
            self.app.processEvents()
            activated.assert_called_once()
        finally:
            first.close()
            second.close()

    def test_gui_commands_survive_cancel_pending_in_worker_queue(self):
        self.window.worker.submit("mensagem a descartar")
        self.window.worker.record("Olá Yuna", "Olá, Kaizen!")
        self.window.worker.cancel_pending()
        self.assertEqual(self.window.worker.queue.get_nowait(),
                         ("record", "Olá Yuna", "Olá, Kaizen!"))
        self.assertTrue(self.window.worker.queue.empty())

    def test_worker_persists_gui_and_chat_once_and_restores_after_reopen(self):
        import sqlite3
        from yuna_desktop import DesktopWorker
        signals = Mock()
        worker = DesktopWorker(signals)
        worker.record("pedido na interface", "resposta da interface")
        worker.submit("mensagem pelo chat")
        worker.queue.put(None)
        with tempfile.TemporaryDirectory() as temp, patch("yuna_desktop.ROOT", Path(temp)), patch(
                "yuna_desktop.LIBRARY") as library:
            library.entries.return_value = []
            def handle(memory, question, *_args, **_kwargs):
                memory.save_turn(question, "resposta do chat")
                return "resposta do chat"
            with patch("yuna_desktop.handle_message", side_effect=handle):
                worker.run()
            with closing(sqlite3.connect(Path(temp) / "data" / "yuna.db")) as db:
                rows = db.execute("SELECT role,content FROM messages ORDER BY id").fetchall()
            self.assertEqual(rows, [("user", "pedido na interface"), ("assistant", "resposta da interface"),
                                    ("user", "mensagem pelo chat"), ("assistant", "resposta do chat")])

    def test_voice_responses_queue_until_playback_finishes_and_stop_discards(self):
        from PySide6.QtMultimedia import QMediaPlayer
        self.window.voice_index = 1
        self.window.voice_busy = True
        self.window.say("próxima resposta")
        self.window.say("resposta posterior")
        with patch("yuna_desktop.Thread") as thread:
            self.window.playback_status(QMediaPlayer.MediaStatus.EndOfMedia)
            thread.return_value.start.assert_called_once()
            self.assertTrue(self.window.voice_busy)
            self.assertEqual(list(self.window._speech_queue), [("resposta posterior", False)])
        self.window.emergency_stop()
        self.assertEqual(list(self.window._speech_queue), [])


if __name__ == "__main__":
    unittest.main()
