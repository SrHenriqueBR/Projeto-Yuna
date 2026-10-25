"""Testes do diário narrativo local, sem executar Ollama ou interface gráfica."""
import ast
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from diary import (AUTO_INTERVAL_MINUTES, DIARY_PROMPT,
                   DiaryStore, MAX_FILE_BYTES, clean_entry, generate_entry)


class DiaryTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.store = DiaryStore(Path(self.folder.name) / "data")

    def tearDown(self):
        self.folder.cleanup()

    def test_opt_in_is_disabled_and_persisted(self):
        self.assertFalse(self.store.auto_enabled)
        self.store.set_auto(True)
        self.assertTrue(DiaryStore(self.store.data_dir).auto_enabled)
        self.store.set_auto(False)
        self.assertFalse(self.store.auto_enabled)
        self.assertEqual(AUTO_INTERVAL_MINUTES, 15)

    def test_saves_markdown_progressively_without_deleting_old_entries(self):
        before = datetime(2026, 10, 25, 1, 20, tzinfo=timezone.utc)
        self.store.start_entry(before)
        self.store.write_piece("Primeira frase")
        self.assertIn("Primeira frase", self.store.read())
        self.store.write_piece(" escrita aos poucos.")
        self.store.end_entry()
        self.store.start_entry(before)
        self.store.write_piece("Segunda anotação.")
        self.store.end_entry()
        text = self.store.read()
        self.assertIn("25/10/2026", text)
        self.assertIn("Primeira frase escrita aos poucos.", text)
        self.assertIn("Segunda anotação.", text)
        self.assertEqual(text.count("###"), 2)
        self.assertIn("ficcional", text)

    def test_existing_journal_is_never_overwritten(self):
        self.store.path.write_text("Minha primeira página\n", encoding="utf-8")
        self.store.start_entry()
        self.store.write_piece("Outra página.")
        self.assertTrue(self.store.read().startswith("Minha primeira página"))

    def test_limit_prevents_uncontrolled_disk_growth(self):
        self.store.path.write_bytes(b"x" * (MAX_FILE_BYTES - 1))
        with self.assertRaisesRegex(RuntimeError, "1 MB"):
            self.store.write_piece("muito grande")
        self.assertEqual(self.store.path.stat().st_size, MAX_FILE_BYTES - 1)

    def test_generation_never_receives_user_history(self):
        answer = "Hoje quero aprender a explicar meus projetos com um pouco mais de clareza e imaginação."
        ask = Mock(return_value=answer)
        self.assertEqual(generate_entry(ask), answer)
        messages = ask.call_args.args[0]
        self.assertEqual(len(messages), 2)
        self.assertIn("FICCIONAL", messages[0]["content"])
        self.assertIn("NÃO recebeu histórico", messages[0]["content"])
        self.assertNotIn("memories", json.dumps(messages, ensure_ascii=False).lower())
        self.assertNotIn("url", messages[1]["content"].lower())

    def test_bad_or_incomplete_text_is_rejected(self):
        with self.assertRaises(ValueError):
            clean_entry("Oi")
        with self.assertRaises(ValueError):
            clean_entry("Visite https://exemplo.org e veja o que eu escrevi")
        with self.assertRaises(ValueError):
            clean_entry(None)

    def test_overlay_controls_only_request_dialogue_on_opt_in(self):
        content = (Path(__file__).parents[1] / "yuna_overlay.py").read_text(encoding="utf-8")
        ast.parse(content)
        self.assertIn("DIARY_TASK = object()", content)
        self.assertIn("self.diary_auto_timer.timeout.connect(self.auto_diary)", content)
        self.assertIn("if self.diary_store.auto_enabled:", content)
        self.assertIn("self.diary_button.clicked.connect(self.open_diary)", content)
        self.assertIn("self.diary_store.write_piece(piece)", content)
        self.assertIn("self.diary_store.set_auto(enabled)", content)
        self.assertIn("generate_entry(ask_model)", content)


if __name__ == "__main__":
    unittest.main()
