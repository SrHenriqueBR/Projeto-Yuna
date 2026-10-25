"""ElevenLabs Amanda Kelly: no-network tests with a fake HTTP response."""
import json
import os
from pathlib import Path
from unittest.mock import patch
import urllib.error
import unittest

import voice


class FakeResponse:
    def __init__(self, media=b"ID3amanda", content_type="audio/mpeg"):
        self.media = media
        self.headers = {"Content-Type": content_type}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, max_bytes):
        return self.media


class AmandaVoiceTests(unittest.TestCase):
    def test_known_catalog_voice_id(self):
        self.assertEqual(voice.AMANDA_VOICE_ID, "oi8rgjIfLgJRsQ6rbZh3")
        self.assertEqual(voice.AMANDA_MODEL, "eleven_multilingual_v2")

    def test_no_api_key_does_not_call_network(self):
        with patch.dict(os.environ, {"ELEVENLABS_API_KEY": ""}), patch(
                "voice.urllib.request.urlopen") as send:
            self.assertFalse(voice.amanda_available())
            with self.assertRaisesRegex(RuntimeError, "ELEVENLABS_API_KEY"):
                voice.synthesize_amanda("Oi, Kaizen.")
            send.assert_not_called()

    def test_synthesis_includes_correct_header_and_text(self):
        with patch.dict(os.environ, {"ELEVENLABS_API_KEY": "test-private-key"}), patch(
                "voice.urllib.request.urlopen",
                return_value=FakeResponse()) as send:
            path = voice.synthesize_amanda("Oi, Kaizen! **Tudo** bem?")
        try:
            self.assertEqual(path.read_bytes(), b"ID3amanda")
            request = send.call_args.args[0]
            self.assertEqual(request.full_url, voice.AMANDA_ENDPOINT)
            self.assertEqual(request.get_method(), "POST")
            self.assertEqual(request.get_header("Xi-api-key"), "test-private-key")
            self.assertEqual(send.call_args.kwargs["timeout"], 60)
            body = json.loads(request.data)
            self.assertEqual(body["model_id"], voice.AMANDA_MODEL)
            self.assertEqual(body["text"], "Oi, Kaizen! Tudo bem?")
            self.assertNotIn("test-private-key", json.dumps(body))
        finally:
            path.unlink(missing_ok=True)

    def test_error_is_safe_to_display_and_does_not_expose_key(self):
        with patch.dict(os.environ, {"ELEVENLABS_API_KEY": "super-secret"}), patch(
                "voice.urllib.request.urlopen",
                side_effect=urllib.error.HTTPError(
                    voice.AMANDA_ENDPOINT, 401,
                    "super-secret", hdrs=None, fp=None)):
            with self.assertRaises(RuntimeError) as failure:
                voice.synthesize_amanda("Olá.")
            self.assertIn("401", str(failure.exception))
            self.assertNotIn("super-secret", str(failure.exception))

    def test_no_audio_is_rejected(self):
        with patch.dict(os.environ, {"ELEVENLABS_API_KEY": "token"}), patch(
                "voice.urllib.request.urlopen",
                return_value=FakeResponse(media=b"", content_type="application/json")):
            with self.assertRaisesRegex(RuntimeError, "não devolveu"):
                voice.synthesize_amanda("Olá Kaizen")


if __name__ == "__main__":
    unittest.main()
