"""Contrato NDJSON, cancelamento de leitura bloqueada e persistência só após conclusão."""
import io
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
from threading import Event, Thread
from time import monotonic
import unittest
from unittest.mock import Mock, patch

from action_diagnostics import LocalModelError
from ollama_stream import chat_stream
import yuna


def events(*rows):
    response = io.BytesIO(b"\n".join(json.dumps(row, ensure_ascii=False).encode("utf-8") for row in rows))
    response.status = 200
    return response


def content(text, done=False, **extra):
    return {"message": {"content": text}, "done": done, **extra}


class StreamTests(unittest.TestCase):
    def call(self, response, **kwargs):
        connection = Mock()
        connection.getresponse.return_value = response
        with patch("ollama_stream.http.client.HTTPConnection", return_value=connection) as factory:
            result = chat_stream({"model": "qwen3.5:4b", "messages": []}, **kwargs)
        self.assertTrue(response.closed)
        connection.close.assert_called_once()
        factory.assert_called_once_with("127.0.0.1", 11434, timeout=5)
        self.assertEqual(connection.request.call_args.args[0:2], ("POST", "/api/chat"))
        self.assertTrue(json.loads(connection.request.call_args.kwargs["body"])["stream"])
        return result

    def test_utf8_chunks_are_joined_and_partial_is_cumulative(self):
        updates = []
        result = self.call(events(content("Olá, "), content("Kaizen!"), content("", True)), on_text=updates.append)
        self.assertEqual(result["message"]["content"], "Olá, Kaizen!")
        self.assertEqual(updates[0], "Olá, ")
        self.assertEqual(updates[-1], "Olá, Kaizen!")

    def test_thinking_and_tool_calls_are_not_exposed(self):
        updates, phases = [], []
        result = self.call(events({"message": {"thinking": "SEGREDO_INTERNO", "tool_calls": [{"name": "execute"}]}, "done": False},
                                  content("Resposta final", True)), on_text=updates.append, on_phase=phases.append)
        self.assertEqual(updates, ["Resposta final"])
        self.assertNotIn("SEGREDO_INTERNO", json.dumps(result) + str(phases))
        self.assertIn("Preparando a resposta…", phases)

    def test_disconnect_without_done_is_an_error(self):
        with self.assertRaisesRegex(LocalModelError, "antes da resposta completa"):
            self.call(events(content("Resposta parcial")))

    def test_invalid_payload_or_server_error_is_not_exposed(self):
        for row in ([], {"error": "C:/Users/PRIVATE secret-token"}, {"message": []},
                    {"message": {"content": 42}, "done": True}):
            with self.subTest(row=row):
                with self.assertRaises(LocalModelError) as error:
                    self.call(events(row))
                self.assertNotIn("PRIVATE", str(error.exception))

    def test_non_json_and_oversized_line_fail_explicitly(self):
        for raw in (b"not-json\n", b"x" * 131073):
            response = io.BytesIO(raw)
            response.status = 200
            with self.assertRaises(LocalModelError):
                self.call(response)

    def test_redirects_and_http_errors_are_not_followed(self):
        for code in (302, 404, 500):
            response = events()
            response.status = code
            with self.subTest(code=code), self.assertRaises(LocalModelError):
                self.call(response)

    def test_pre_cancel_does_not_connect(self):
        with patch("ollama_stream.http.client.HTTPConnection") as factory:
            with self.assertRaises(InterruptedError):
                chat_stream({}, cancelled=lambda: True)
            factory.assert_not_called()

    def test_stop_unblocks_pending_read_and_closes_connection(self):
        reading, closed, stop = Event(), Event(), Event()
        connection = Mock()
        connection.sock.shutdown.side_effect = lambda *args: closed.set()
        response = Mock(status=200)
        def read(*args):
            reading.set()
            if not closed.wait(2):
                raise AssertionError("Cancelamento não fechou o transporte")
            return b""
        response.readline.side_effect = read
        connection.getresponse.return_value = response
        failures = []
        def run():
            try:
                chat_stream({"model": "local"}, cancelled=stop.is_set)
            except BaseException as exc:
                failures.append(exc)
        with patch("ollama_stream.http.client.HTTPConnection", return_value=connection):
            worker = Thread(target=run)
            worker.start()
            self.assertTrue(reading.wait(2))
            start = monotonic()
            stop.set()
            worker.join(2)
            self.assertFalse(worker.is_alive())
            self.assertLess(monotonic() - start, 1.5)
        self.assertEqual(len(failures), 1)
        self.assertIsInstance(failures[0], InterruptedError)
        connection.sock.shutdown.assert_called_once()
        response.close.assert_called_once()
        connection.close.assert_called_once()

    def test_deadline_unblocks_idle_read(self):
        closed = Event()
        connection = Mock()
        connection.sock.shutdown.side_effect = lambda *args: closed.set()
        response = Mock(status=200)
        def read(*args):
            self.assertTrue(closed.wait(2))
            return b""
        response.readline.side_effect = read
        connection.getresponse.return_value = response
        with patch("ollama_stream.http.client.HTTPConnection", return_value=connection):
            with self.assertRaises(TimeoutError):
                chat_stream({"model": "local"}, timeout=.1)

    def test_cancel_at_last_chunk_does_not_report_success(self):
        stop = Event()
        with self.assertRaises(InterruptedError):
            self.call(events(content("Texto", True)), on_text=lambda text: stop.set(), cancelled=stop.is_set)

    def test_real_http_socket_can_be_cancelled_while_server_is_silent(self):
        started, release, stop = Event(), Event(), Event()
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_POST(self):
                self.rfile.read(int(self.headers["Content-Length"]))
                self.send_response(200)
                self.send_header("Content-Type", "application/x-ndjson")
                self.end_headers()
                self.wfile.write(json.dumps(content("Começando")).encode("utf-8") + b"\n")
                self.wfile.flush()
                started.set()
                release.wait(5)
        try:
            server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        except PermissionError:
            self.skipTest("Socket local indisponível neste executor")
        serving = Thread(target=lambda: server.serve_forever(poll_interval=.02), daemon=True)
        serving.start()
        original = http.client.HTTPConnection
        failures = []
        def run():
            try:
                chat_stream({"model": "teste-local", "messages": []}, cancelled=stop.is_set)
            except BaseException as exc:
                failures.append(exc)
        try:
            with patch("ollama_stream.http.client.HTTPConnection",
                       side_effect=lambda host, port, timeout: original(host, server.server_port, timeout=timeout)):
                worker = Thread(target=run)
                worker.start()
                self.assertTrue(started.wait(5))
                stop.set()
                worker.join(2)
                self.assertFalse(worker.is_alive(), "A leitura HTTP permaneceu bloqueada")
            self.assertEqual(len(failures), 1)
            self.assertIsInstance(failures[0], InterruptedError)
        finally:
            stop.set()
            release.set()
            server.shutdown()
            server.server_close()
            serving.join(2)


class StreamIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.memory = yuna.Memory(Path(self.tmp.name) / "yuna.db")

    def tearDown(self):
        self.memory.close()
        self.tmp.cleanup()

    def test_partial_is_not_stored_before_final_answer(self):
        states = []
        def generate(payload, **kwargs):
            kwargs["on_text"]("Uma resposta parcial")
            states.append(self.memory.history())
            return {"message": {"content": "Uma resposta concluída."}, "done": True}
        with patch("ollama_stream.chat_stream", side_effect=generate):
            reply = yuna.respond(self.memory, "Converse sobre criatividade", allow_research=False,
                                  on_text=lambda text: None)
        self.assertEqual(states, [[]])
        self.assertEqual(reply, "Uma resposta concluída.")
        self.assertEqual(self.memory.history()[-1]["content"], reply)
        self.assertIsNotNone(self.memory.teaching.last_answer())

    def test_incomplete_stream_does_not_save_history_or_teaching_candidate(self):
        def generate(payload, **kwargs):
            kwargs["on_text"]("Uma resposta parcial")
            raise LocalModelError("Conexão interrompida")
        with patch("ollama_stream.chat_stream", side_effect=generate):
            with self.assertRaises(LocalModelError):
                yuna.respond(self.memory, "Converse sobre criatividade", allow_research=False, on_text=lambda text: None)
        self.assertEqual(self.memory.history(), [])
        self.assertIsNone(self.memory.teaching.last_answer())

    def test_empty_thinking_retries_once_without_exposing_internal_text(self):
        results = [{"message": {"content": ""}, "done": True},
                   {"message": {"content": "print(1)"}, "done": True}]
        settings = []
        def generate(payload, **kwargs):
            settings.append(dict(payload))
            return results.pop(0)
        with patch("yuna.current_model", return_value="qwen3.5:4b"), \
             patch("yuna.load_profile", return_value="maximo"), \
             patch("ollama_stream.chat_stream", side_effect=generate):
            result = yuna.ask_model([], purpose="code", on_text=lambda text: None)
        self.assertEqual(result, "print(1)")
        self.assertTrue(settings[0]["think"])
        self.assertFalse(settings[1]["think"])

    def test_length_limit_warns_and_structured_output_is_never_previewed(self):
        final = {"message": {"content": "parcial"}, "done": True, "done_reason": "length"}
        with patch("ollama_stream.chat_stream", return_value=final) as stream:
            text = yuna.ask_model([], on_text=Mock())
            self.assertIn("código pode estar incompleto", text)
            with self.assertRaises(LocalModelError):
                yuna.ask_model([], schema={"type": "object"}, on_text=Mock())
            self.assertIsNone(stream.call_args.kwargs["on_text"])

    def test_cancelled_tool_inference_cannot_open_application(self):
        stop = Event()
        computer = Mock()
        computer.handle.return_value = None
        def infer(*args, **kwargs):
            stop.set()
            return json.dumps({"action": "open_app", "query": "discord", "everywhere": False})
        with patch("yuna.ask_model", side_effect=infer):
            with self.assertRaises(InterruptedError):
                yuna.handle_message(self.memory, "/fazer encontre o aplicativo Discord e abra",
                                    computer=computer, cancelled=stop.is_set)
        computer.desktop.open_app.assert_not_called()


if __name__ == "__main__":
    unittest.main()
