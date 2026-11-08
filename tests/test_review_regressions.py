"""Falhas de uso real: cancelamento, modelos Qwen e migração de índices."""
from contextlib import ExitStack, closing
import importlib.util
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
from threading import Event
import unittest
from unittest.mock import Mock, patch

import yuna
import yuna_rag
import windows_events
from app_maintenance import import_legacy_data


class ConversationRegressionTests(unittest.TestCase):
    def test_model_error_preserves_recovery_guidance_without_raw_service_details(self):
        from action_diagnostics import diagnose_failure
        from urllib.error import HTTPError, URLError
        for failure in (URLError("internal secret"),
                        HTTPError("url", 404, "private server message", {}, None)):
            with self.subTest(failure=type(failure).__name__), patch(
                    "yuna.urllib.request.build_opener") as build:
                build.return_value.open.side_effect = failure
                with self.assertRaises(RuntimeError) as caught:
                    yuna.ask_model([])
                advice = diagnose_failure(caught.exception).message()
                self.assertIn("Ollama", advice)
                self.assertIn("Central da Yuna", advice)
                self.assertNotIn("internal secret", advice)
                self.assertNotIn("private server message", advice)

    def test_other_local_models_keep_their_thinking_defaults(self):
        with patch("yuna.current_model", return_value="qwen2.5:3b"), patch(
                "yuna.urllib.request.build_opener") as build:
            build.return_value.open.return_value = io.BytesIO(b'{"message":{"content":"Oi"}}')
            yuna.ask_model([])
            self.assertNotIn("think", json.loads(build.return_value.open.call_args.args[0].data))

    def test_cancel_during_inference_does_not_save_or_revise_old_answer(self):
        with tempfile.TemporaryDirectory() as folder:
            memory = yuna.Memory(Path(folder) / "yuna.db")
            stopped = Event()
            def answer(*args, **kwargs):
                stopped.set()
                return "vou consegue"  # A revisão também não deve iniciar após Parar.
            try:
                with patch("yuna.ask_model", side_effect=answer) as model, patch.dict(
                        "os.environ", {"YUNA_AUTO_RESEARCH": "0"}):
                    with self.assertRaises(InterruptedError):
                        yuna.handle_message(memory, "Uma história curta sobre um farol em Marte",
                                            cancelled=stopped.is_set)
                model.assert_called_once()
                self.assertEqual(memory.history(), [])
            finally:
                memory.close()

    def test_qwen35_uses_answer_budget_without_hidden_thinking(self):
        for model in ("qwen3.5:2b", "qwen3.5:4b", "qwen3.5:9b"):
            for purpose in ("conversation", "code"):
                with self.subTest(model=model, purpose=purpose), patch("yuna.current_model", return_value=model), patch(
                        "yuna.urllib.request.build_opener") as build:
                    build.return_value.open.return_value = io.BytesIO(
                        b'{"message":{"content":"Resposta pronta"}}')
                    with patch("yuna.load_profile", return_value="equilibrado"):
                        self.assertEqual(yuna.ask_model([], purpose=purpose), "Resposta pronta")
                    payload = json.loads(build.return_value.open.call_args.args[0].data)
                    self.assertIs(payload.get("think"), False)

    def test_local_chat_refuses_http_redirects(self):
        with patch("yuna.urllib.request.build_opener") as build:
            build.return_value.open.return_value = io.BytesIO(b'{"message":{"content":"Oi"}}')
            yuna.ask_model([])
        from urllib.request import HTTPRedirectHandler, Request
        handlers = [h for h in build.call_args.args if isinstance(h, HTTPRedirectHandler)]
        self.assertEqual(len(handlers), 1)
        for status in (301, 302, 303, 307, 308):
            with self.subTest(status=status):
                self.assertIsNone(handlers[0].redirect_request(
                    Request("http://127.0.0.1:11434/api/chat", data=b"private"),
                    None, status, "redirect", {}, "https://example.com/"))


@unittest.skipUnless(importlib.util.find_spec("PySide6"), "Qt não instalado")
class WorkerRegressionTests(unittest.TestCase):
    def run_worker(self, worker, **stubs):
        with ExitStack() as stack:
            memory = stack.enter_context(patch("yuna_desktop.Memory"))
            stack.enter_context(patch("yuna_desktop.Computer"))
            library = stack.enter_context(patch("yuna_desktop.LIBRARY"))
            library.entries.return_value = []
            memory.return_value.db.execute.return_value.fetchall.return_value = []
            memory.return_value.db.execute.return_value.fetchone.return_value = (None,)
            for name, callback in stubs.items():
                stack.enter_context(patch("yuna_desktop." + name, side_effect=callback))
            worker.run()
        return memory.return_value

    def test_new_document_analysis_works_after_stop_without_sending_chat_first(self):
        from yuna_desktop import DesktopWorker
        signals = Mock()
        worker = DesktopWorker(signals)
        worker.cancel_pending()
        worker.analyze("documento.txt", "Resuma")
        worker.queue.put(None)
        self.run_worker(worker, analyze_document=lambda *a: "Análise nova")
        signals.replied.emit.assert_called_once_with("Análise nova", True)

    def test_cancelled_document_does_not_reappear_when_new_chat_is_sent(self):
        from yuna_desktop import DesktopWorker
        signals = Mock()
        worker = DesktopWorker(signals)
        worker.analyze("antigo.txt", "Resuma")
        def analyze(*args):
            worker.cancel_pending()
            worker.submit("pedido novo")
            worker.queue.put(None)
            return "Análise antiga"
        self.run_worker(worker, analyze_document=analyze,
                        handle_message=lambda *a, **kw: "Resposta nova")
        signals.replied.emit.assert_called_once_with("Resposta nova", False)
        self.assertNotIn("Análise concluída • arquivo não guardado",
                         [c.args[0] for c in signals.status.emit.call_args_list])

    def test_cancelled_fallback_reply_is_not_saved_and_stale_errors_are_ignored(self):
        from yuna_desktop import DesktopWorker
        for failure in (False, True):
            with self.subTest(failure=failure):
                signals = Mock()
                worker = DesktopWorker(signals)
                worker.submit("antigo")
                def handle(memory, text, *args, **kwargs):
                    if text == "antigo":
                        worker.cancel_pending()
                        worker.submit("novo")
                        worker.queue.put(None)
                        if failure:
                            raise RuntimeError("Falha antiga")
                        return "Resposta antiga"
                    return "Resposta nova"
                memory = self.run_worker(worker, handle_message=handle)
                memory.save_turn.assert_called_once_with("novo", "Resposta nova")
                signals.error.emit.assert_not_called()
                signals.replied.emit.assert_called_once_with("Resposta nova", False)


class MigrationRegressionTests(unittest.TestCase):
    def test_rag_sqlite_with_wal_migrates_confirmed_rows(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            old, new = root / "antiga", root / "nova"
            (old / "data").mkdir(parents=True)
            for filename in ("yuna_rag.sqlite", "indice.sqlite3"):
                with self.subTest(filename=filename), closing(sqlite3.connect(old / "data" / filename)) as db:
                    db.execute("PRAGMA journal_mode=WAL")
                    db.execute("CREATE TABLE chunks(content TEXT)")
                    db.execute("INSERT INTO chunks VALUES ('Documento preservado')")
                    db.commit()
                    destination = new / filename
                    import_legacy_data(old, destination)
                    with closing(sqlite3.connect(destination / "data" / filename)) as copied:
                        self.assertEqual(copied.execute("SELECT content FROM chunks").fetchone(),
                                         ("Documento preservado",))

    def test_rag_reports_partial_extraction(self):
        from document_library import DocumentLibrary
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "grande.txt"
            source.write_text("conteúdo " * 4000, encoding="utf-8")
            entry = DocumentLibrary(root / "data").add(source)
            with patch("yuna_rag.embeddings", side_effect=lambda xs: [[1.0, 0.0] for _ in xs]):
                result = yuna_rag.index_document(root, entry["id"])
            self.assertIn("Texto parcial", result)
            self.assertTrue(source.exists())


@unittest.skipUnless(os.name == "nt", "PowerShell 5.1 verificado no Windows")
class WindowsEventEncodingTests(unittest.TestCase):
    def query(self, stub):
        # Executa o PowerShell real com eventos de teste; não lê logs da máquina.
        def runner(args, **kwargs):
            return subprocess.run([*args[:-1], stub + "; " + args[-1]], **kwargs)
        return windows_events.read_recent_events("System", runner=runner)

    def test_native_powershell_preserves_portuguese(self):
        text = self.query("function Get-WinEvent { [pscustomobject]@{"
                          "TimeCreated=[datetime]'2026-11-05T12:00:00'; "
                          "ProviderName='Aplicação de teste'; Id=42; LevelDisplayName='Crítico'} }")
        self.assertIn("Aplicação de teste", text)
        self.assertIn("Crítico", text)
        self.assertIn("Evento 42", text)

    def test_no_matching_events_is_empty_and_access_denied_is_not(self):
        no_events = self.query("function Get-WinEvent { Write-Error 'No events' "
                               "-ErrorId NoMatchingEventsFound -ErrorAction Stop }")
        self.assertIn("Nenhum evento", no_events)
        denied = self.query("function Get-WinEvent { throw 'Access denied' }")
        self.assertIn("Não consegui ler", denied)
        self.assertNotIn("Nenhum evento", denied)


if __name__ == "__main__":
    unittest.main()
