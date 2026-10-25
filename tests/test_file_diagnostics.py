"""A criação de arquivos é verificada sem Ollama, sem GUI nem Word instalado."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import file_diagnostics
import yuna
from document_writer import FileRequest, generate_contents


class FileDiagnosticTests(unittest.TestCase):
    def test_local_probe_actually_creates_txt_at_real_folder(self):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root)
            with patch("file_diagnostics.known_folder", return_value=folder):
                first = file_diagnostics.create_test_file()
                second = file_diagnostics.create_test_file()
            self.assertIn(str(folder), first)
            self.assertIn("Yuna_Teste_Arquivo.txt", first)
            self.assertIn("Yuna_Teste_Arquivo (2).txt", second)
            self.assertIn("Yuna", (folder / "Yuna_Teste_Arquivo.txt").read_text(encoding="utf-8"))
            self.assertGreater((folder / "Yuna_Teste_Arquivo (2).txt").stat().st_size, 0)

    def test_runtime_report_discloses_real_version_and_executable(self):
        report = file_diagnostics.runtime_report("0.12.2", Path(__file__).parents[1])
        self.assertIn("Yuna versão 0.12.2", report)
        self.assertIn("Python em execução:", report)
        self.assertIn("Gerador de documentos:", report)
        self.assertIn("python-docx:", report)

    def test_message_routed_to_diagnostic_not_model(self):
        with patch("yuna.ask_model") as model, patch(
                "yuna.create_test_file", return_value="Criei TXT real") as probe:
            result = yuna.handle_message(None, "/teste_arquivo", None)
            self.assertEqual(result, "Criei TXT real")
            probe.assert_called_once()
            model.assert_not_called()

    def test_version_diagnostic_does_not_call_model(self):
        with patch("yuna.ask_model") as model:
            result = yuna.handle_message(None, "/versao", None)
            self.assertIn("Yuna versão", result)
            model.assert_not_called()

    def test_content_retry_when_model_only_tells_user_to_open_word(self):
        model_response = iter([
            "Você vai precisar abrir o Word primeiro. Use o comando /abrir 1 no terminal.",
            "Este é o primeiro capítulo do Diário da Yuna, escrito como narrativa ficcional.\n\n"
            "Vou continuar construindo esta história aos poucos e revisando o que escrevo."
        ])
        def ask(messages):
            return next(model_response)
        req = FileRequest("word", "Diário da Yuna", Path("."))
        result = generate_contents(req, ask)
        self.assertIn("primeiro capítulo", result)
        self.assertNotIn("/abrir", result)

    def test_does_not_claim_file_saved_for_failed_model(self):
        req = FileRequest("word", "Diário da Yuna", Path("."))
        with self.assertRaisesRegex(ValueError, "Nada foi salvo"):
            generate_contents(req, lambda messages: "Abra o Word primeiro e use /abrir 1")


if __name__ == "__main__":
    unittest.main()
