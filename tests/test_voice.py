"""Validação de voz: não depende de internet nem de hardware."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import sys
import unittest

import voice


class VoiceTests(unittest.TestCase):
    def test_filtering_and_limits(self):
        self.assertEqual(voice.speech_text("Oi, **Kaizen**!"), "Oi, Kaizen!")
        self.assertEqual(voice.speech_text("Confira https://exemplo.org/arquivo"), "Confira um link")
        self.assertEqual(voice.speech_text("x" * 1000, 100), "x" * 100 + "...")
        self.assertEqual(voice.speech_text(None), "")
        self.assertEqual(voice.speech_text(""), "")

    def test_female_voice_and_local_privacy(self):
        self.assertEqual(voice.EDGE_VOICE, "pt-BR-FranciscaNeural")
        self.assertIn("Gender -eq 'Female'", voice.WINDOWS_SCRIPT)
        self.assertIn("pt-BR", voice.WINDOWS_SCRIPT)
        self.assertIn("[Console]::In.ReadToEnd()", voice.WINDOWS_SCRIPT)
        self.assertNotIn("http", voice.WINDOWS_SCRIPT.lower())

    def test_optin_edge_stream_to_temporary_file(self):
        parameters = {}

        class FakeCommunicate:
            def __init__(self, text, name, rate, pitch):
                parameters.update(text=text, name=name, rate=rate, pitch=pitch)

            async def save(self, filename):
                Path(filename).write_bytes(b"ID3fake")

        with patch.dict(sys.modules, {"edge_tts": SimpleNamespace(Communicate=FakeCommunicate)}):
            output = voice.synthesize_edge("Oi, Kaizen!")
        try:
            self.assertTrue(output.exists())
            self.assertTrue(output.read_bytes().startswith(b"ID3"))
            self.assertEqual(parameters["name"], "pt-BR-FranciscaNeural")
            self.assertEqual(parameters["rate"], "+13%")
            self.assertEqual(parameters["pitch"], "+8Hz")
        finally:
            output.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
