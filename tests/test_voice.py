"""Validação de voz: não depende de internet nem de hardware."""
from pathlib import Path
from types import ModuleType
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

        edge_package = ModuleType("edge_tts")
        edge_package.__path__ = []
        submodule = ModuleType("edge_tts.communicate")
        submodule.Communicate = FakeCommunicate
        with patch.dict(sys.modules, {"edge_tts": edge_package,
                                      "edge_tts.communicate": submodule}):
            output = voice.synthesize_edge("Oi, Kaizen!")
        try:
            self.assertTrue(output.exists())
            self.assertTrue(output.read_bytes().startswith(b"ID3"))
            self.assertEqual(parameters["name"], "pt-BR-FranciscaNeural")
            self.assertEqual(parameters["rate"], "+13%")
            self.assertEqual(parameters["pitch"], "+8Hz")
        finally:
            output.unlink(missing_ok=True)


    def test_lazy_import_failure_has_stable_python_fallback(self):
        async def broken(*args):
            raise TypeError("'lazy_import' object is not callable")

        def fake_stable(text, filename):
            self.assertIn("Kaizen", text)
            Path(filename).write_bytes(b"ID3fallback")

        with patch("voice._edge_save", side_effect=broken), patch(
                "voice._stable_python_edge", side_effect=fake_stable) as fallback:
            audio = voice.synthesize_edge("Oi Kaizen!")
        try:
            self.assertEqual(audio.read_bytes(), b"ID3fallback")
            fallback.assert_called_once()
        finally:
            audio.unlink(missing_ok=True)

    def test_other_typeerror_is_not_hidden(self):
        async def broken(*args):
            raise TypeError("Erro de parâmetros")
        with patch("voice._edge_save", side_effect=broken), patch(
                "voice._stable_python_edge") as fallback:
            with self.assertRaisesRegex(TypeError, "parâmetros"):
                voice.synthesize_edge("Texto de teste")
            fallback.assert_not_called()

    def test_fallback_gives_a_readable_installation_message(self):
        path = Path("resultado.mp3")
        with patch("voice.os.name", "nt"), patch("voice.shutil.which", return_value="py"), patch(
                "voice.subprocess.run", return_value=SimpleResult(1)):
            with self.assertRaisesRegex(RuntimeError, "py -3.13 -m pip install edge-tts"):
                voice._stable_python_edge("Teste", path)


class SimpleResult:
    def __init__(self, returncode):
        self.returncode = returncode
        self.stderr = "Não instalado"


if __name__ == "__main__":
    unittest.main()
