"""Regression: long free-form conversations must not hit planner/CLI/UI size caps."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import agent_brain
import yuna


class LongMessagesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.memory = yuna.Memory(Path(self.temp.name) / "yuna.db")

    def tearDown(self):
        self.memory.close()
        self.temp.cleanup()

    def test_plain_long_message_is_not_a_plan_or_error(self):
        message = (
            "Kaizen, quero conversar sobre como a Yuna pode aprender mais e "
            "ter iniciativa sem controlar nada por conta própria. "
        ) * 125
        self.assertGreater(len(message), 6000)
        self.assertIsNone(agent_brain.plan_request(message))
        with patch("yuna.ask_model", return_value="Entendi, Kaizen. Vamos conversar!") as ask:
            reply = yuna.handle_message(self.memory, message)
        self.assertIn("Entendi", reply)
        self.assertEqual(ask.call_count, 1)
        self.assertEqual(ask.call_args.args[0][-1]["content"], message)
        self.assertEqual(self.memory.db.execute(
            "SELECT content FROM messages WHERE role='user' ORDER BY id DESC LIMIT 1"
        ).fetchone()[0], message)

    def test_large_text_that_mentions_activities_stays_conversation(self):
        message = (
            "Tenho uma ideia: quero conversar sobre pesquisas, programas, "
            "criar documentos e aprender de modo natural; não é uma ordem agora. "
        ) * 100
        self.assertIsNone(agent_brain.plan_request(message))
        with patch("yuna.ask_model", return_value="Legal, vamos discutir a ideia."):
            self.assertIn("Legal", yuna.handle_message(self.memory, message))

    def test_real_multi_step_short_request_still_plans(self):
        with tempfile.TemporaryDirectory() as home:
            from pathlib import Path
            for folder in ("Documents", "Downloads", "Desktop"):
                (Path(home) / folder).mkdir()
            plan = agent_brain.plan_request(
                "Pesquise sobre astronomia, crie um Word em Documentos", Path(home)
            )
        self.assertIsNotNone(plan)
        self.assertEqual(plan.output.kind, "word")

    def test_console_no_arbitrary_chat_limit(self):
        source = (Path(__file__).resolve().parents[1] / "yuna.py").read_text(encoding="utf-8")
        self.assertNotIn("elif len(text) > 4000:", source)
        self.assertNotIn("Envie até 4000 caracteres por mensagem.", source)
        planner = (Path(__file__).resolve().parents[1] / "agent_brain.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("Pedido muito longo: máximo de 600 caracteres.", planner)

    def test_mascot_multiline_input_does_not_clip_text(self):
        source = (Path(__file__).resolve().parents[1] / "yuna_overlay.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("class LongMessageInput(QPlainTextEdit)", source)
        self.assertIn("self.entry = LongMessageInput()", source)
        self.assertIn("self.entry.toPlainText().strip()", source)
        self.assertIn("self.entry.submitRequested.connect(self.send)", source)
        self.assertNotIn("self.entry.setMaxLength(2000)", source)
        self.assertNotIn("self.entry.text().strip()", source)


if __name__ == "__main__":
    unittest.main()
