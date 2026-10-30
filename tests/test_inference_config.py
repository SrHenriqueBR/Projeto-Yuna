from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import inference_config as config
import yuna


class PerformanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_default_and_persistent_revert(self):
        self.assertEqual(config.load_profile(self.root), "equilibrado")
        config.save_profile(self.root, "rapido")
        self.assertEqual(config.load_profile(self.root), "rapido")
        self.assertEqual(config.options_for(self.root)["num_predict"], 384)
        config.save_profile(self.root, "equilibrado")
        self.assertEqual(config.options_for(self.root)["num_predict"], 768)
        with self.assertRaises(ValueError):
            config.save_profile(self.root, "unlimited")

    def test_corrupt_or_unknown_config_uses_bounded_default(self):
        path = config.profile_path(self.root)
        path.parent.mkdir()
        for value in ('{"num_predict":999999}', '"unlimited"', 'not JSON'):
            path.write_text(value)
            self.assertEqual(config.load_profile(self.root), "equilibrado")

    def test_fast_profile_changes_actual_request_but_keeps_json_and_code_budget(self):
        config.save_profile(self.root, "rapido")
        with patch("yuna.ROOT", self.root), patch("yuna.urllib.request.build_opener") as build:
            for schema, purpose, expected in ((None, "conversation", 384), ({"type": "object"}, "conversation", 768),
                                               ({"type": "object"}, "code", 3072)):
                build.return_value.open.return_value = BytesIO(b'{"message":{"content":"Resposta"}}')
                yuna.ask_model([{"role": "user", "content": "Teste"}], schema=schema, purpose=purpose)
                data = json.loads(build.return_value.open.call_args.args[0].data)
                self.assertEqual(data["keep_alive"], "5m")
                self.assertEqual(data["options"]["num_predict"], expected)
                self.assertEqual(data["stream"], False)
                self.assertEqual(build.return_value.open.call_args.args[0].full_url, "http://127.0.0.1:11434/api/chat")

    def test_command_updates_profile_without_ollama_or_model_download(self):
        with patch("yuna.ROOT", self.root), patch("yuna.ask_model", side_effect=AssertionError("No model")):
            self.assertIn("rapido", yuna.handle_message(None, "/desempenho rapido"))
            self.assertEqual(config.load_profile(self.root), "rapido")


if __name__ == "__main__":
    unittest.main()
