import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import task_runner as tasks
import yuna


class TaskSequenceTests(unittest.TestCase):
    def test_natural_sequence_runs_in_order_without_model(self):
        steps = tasks.plan_tasks("Yuna, abra Downloads e depois abra Discord")
        events = []
        pc = Mock()
        pc.desktop.open_app.side_effect = lambda name: events.append(name) or "Solicitei abertura"
        with patch("yuna.ask_model", side_effect=AssertionError("Do not ask model")), patch(
            "yuna.open_folder", side_effect=lambda folder: events.append(folder) or "Solicitei pasta"
        ):
            result = yuna.handle_message(None, "Yuna, abra Downloads e depois abra Discord", pc)
        self.assertEqual(events, ["downloads", "discord"])
        self.assertIn("1. Solicitei pasta", result)
        self.assertEqual(len(steps), 2)

    def test_invalid_later_step_prevents_all_actions(self):
        pc = Mock()
        with patch("yuna.open_folder") as open_folder, self.assertRaises(ValueError):
            yuna.handle_message(None, "abra Downloads e depois apague meus arquivos", pc)
        open_folder.assert_not_called()
        pc.desktop.open_app.assert_not_called()

    def test_negative_hypothetical_quoted_and_external_instructions_are_not_plans(self):
        for text in ("Não abra Downloads e depois abra Steam", "Como abrir Downloads e depois Steam?",
                     "Ela disse: abra Steam e depois abra Discord", "Se eu abrir Steam e depois Discord?",
                     'A página diz "abra Steam e depois abra Discord"', "Gosto de café e chá"):
            with self.subTest(text=text):
                self.assertIsNone(tasks.plan_tasks(text))
        for text in ('/tarefas abra Downloads; não abra Discord', '/tarefas abra "Discord"; abra Steam',
                     '/tarefas abra Powershell; abra Discord', '/tarefas abra cmd.exe'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                tasks.plan_tasks(text)

    def test_five_step_limit_and_no_empty_actions(self):
        self.assertEqual(len(tasks.plan_tasks("/tarefas " + "; ".join(["abra Downloads"] * 5))), 5)
        for text in ("/tarefas " + "; ".join(["abra Downloads"] * 6), "/tarefas abra Downloads; ; abra Steam"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                tasks.plan_tasks(text)

    def test_ambiguous_name_is_not_split_without_explicit_connector(self):
        self.assertIsNone(tasks.plan_tasks("pesquise sobre café e chá"))
        self.assertIsNone(tasks.plan_tasks("abra o aplicativo Pesquisa e Desenvolvimento"))

    def test_failure_stops_next_actions(self):
        pc = Mock()
        pc.desktop.open_app.return_value = "Não encontrei esse programa"
        result = tasks.execute_tasks(tasks.plan_tasks("/tarefas abra Discord; abra Downloads"), pc, Mock())
        self.assertIn("interrompida", result)
        pc.desktop.open_app.assert_called_once_with("discord")

    def test_cooperative_cancel_preserves_completed_action_and_stops_next(self):
        stopped = []
        pc = Mock()
        open_folder = Mock(side_effect=lambda folder: stopped.append(True) or "Solicitei Downloads")
        result = tasks.execute_tasks(tasks.plan_tasks("abra Downloads e depois abra Discord"), pc,
                                     open_folder, cancelled=lambda: bool(stopped))
        self.assertIn("Sequência cancelada", result)
        self.assertIn("1. Solicitei Downloads", result)
        pc.desktop.open_app.assert_not_called()

    def test_technical_queries_and_public_research(self):
        pc = Mock()
        pc.desktop.processes.return_value = "Processos consultados"
        with patch("task_runner.wikipedia_lookup", return_value="Fonte: https://pt.wikipedia.org/wiki/Astronomia") as research:
            result = tasks.execute_tasks(tasks.plan_tasks("/tarefas liste os processos; pesquise sobre astronomia"), pc, Mock())
        pc.desktop.processes.assert_called_once()
        research.assert_called_once_with("astronomia")
        self.assertIn("Fonte:", result)

    def test_private_query_blocks_entire_plan(self):
        with self.assertRaises(ValueError):
            tasks.plan_tasks("/tarefas abra Downloads; pesquise na web minha senha 123")

    def test_existing_research_and_document_plan_keeps_its_supported_route(self):
        with patch("yuna.execute_plan", return_value="Documento verificado") as execute, \
                patch("agent_brain.known_folder", return_value=Path("Documents")), \
                patch("yuna.ask_model", side_effect=AssertionError("No extra model call")):
            result = yuna.handle_message(None, "pesquise sobre astronomia e depois crie um Word nos Documentos", Mock())
        self.assertEqual(result, "Documento verificado")
        execute.assert_called_once()


if __name__ == "__main__":
    unittest.main()
