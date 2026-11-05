"""A Central instala somente modelos locais após confirmação e download concluído."""
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app_tools import installation_status, local_api, prepare_model
from model_config import INSTALLER_MODELS, load_selected_model


class ModelDownloadTests(unittest.TestCase):
    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory()
        self.root = Path(self.workspace.name)
        self.data = self.root / "data"
        self.data.mkdir()
        self.memory = self.data / "yuna.db"
        self.memory.write_bytes(b"SQLITE-PRIVATE-MEMORY")

    def tearDown(self):
        self.workspace.cleanup()

    def test_each_official_qwen35_is_allowed_and_selected_only_on_success(self):
        for model in ("qwen3.5:2b", "qwen3.5:4b", "qwen3.5:9b"):
            with self.subTest(model=model):
                calls = []
                def stub(path, payload=None, timeout=5):
                    calls.append((path, payload, timeout))
                    return io.BytesIO(b'{"status":"downloading","total":100,"completed":25}\n'
                                      b'{"status":"success"}\n')
                with patch("app_tools.local_api", side_effect=stub):
                    progress = []
                    text = prepare_model(self.root, model, progress.append)
                self.assertEqual(load_selected_model(self.root, {}), model)
                self.assertIn(model, text)
                self.assertEqual(len(calls), 1)
                self.assertEqual(calls[0][0], "/api/pull")
                self.assertEqual(calls[0][1], {"model": model, "stream": True})
                self.assertTrue(any("25%" in line for line in progress))
                self.assertEqual(self.memory.read_bytes(), b"SQLITE-PRIVATE-MEMORY")

    def test_paid_and_unknown_models_never_connect_to_api(self):
        invalid = ("qwen3.5:cloud", "qwen2.5:cloud", "qwen3.5:27b",
                   "https://api.qwen.ai", "paid", "", "../secret")
        with patch("app_tools.local_api") as endpoint:
            for model in invalid:
                with self.subTest(model=model):
                    with self.assertRaises(ValueError):
                        prepare_model(self.root, model)
            endpoint.assert_not_called()
        self.assertTrue(all("cloud" not in m for m in INSTALLER_MODELS))

    def test_failed_or_partial_download_keeps_previous_selection(self):
        old = "qwen2.5:3b"
        self.assertEqual(load_selected_model(self.root, {}), old)
        cases = (
            b'{"status":"downloading","total":10,"completed":3}\n',
            b'{"error":"not enough space"}\n',
            b'{"status":"downloading"}\ninvalid-json\n',
        )
        for response in cases:
            with self.subTest(response=response):
                with patch("app_tools.local_api", return_value=io.BytesIO(response)):
                    with self.assertRaises((RuntimeError, ValueError)):
                        prepare_model(self.root, "qwen3.5:4b")
                self.assertEqual(load_selected_model(self.root, {}), old)
                self.assertEqual(self.memory.read_bytes(), b"SQLITE-PRIVATE-MEMORY")

    def test_api_targets_only_ollama_loopback_without_proxy(self):
        class FakeOpener:
            def __init__(self):
                self.received = None

            def open(self, request, timeout):
                self.received = request.full_url
                return io.BytesIO(b'{"models":[]}')
        opener = FakeOpener()
        with patch("app_tools.urllib.request.build_opener", return_value=opener) as factory:
            with local_api("/api/tags") as response:
                self.assertEqual(response.read(), b'{"models":[]}')
        self.assertEqual(opener.received, "http://127.0.0.1:11434/api/tags")
        args = factory.call_args.args
        self.assertTrue(any(isinstance(handler, type(__import__("urllib").request.ProxyHandler({})))
                            for handler in args))

    def test_status_does_not_require_cloud_credentials(self):
        with patch("app_tools.local_api", return_value=io.BytesIO(b'{"models":[]}')):
            text = installation_status(self.root)
        self.assertIn("Qwen3.5", text)
        self.assertIn("LOCAL", text)
        self.assertIn("Ollama", text)


if __name__ == "__main__":
    unittest.main()
