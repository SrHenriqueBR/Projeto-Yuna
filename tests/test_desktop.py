from pathlib import Path
import unittest
from unittest.mock import patch, Mock
import subprocess
import desktop
import computer
import local_agent
import yuna
import json

APPS = [{'Name': 'Discord', 'AppID': 'Discord.App'},
        {'Name': 'Google Chrome', 'AppID': 'Chrome'},
        {'Name': 'Editor Alpha', 'AppID': 'Editor.A'},
        {'Name': 'Editor Beta', 'AppID': 'Editor.B'}]

class DesktopTests(unittest.TestCase):
    @patch('desktop.query_windows', return_value=APPS)
    def test_discovery_matching_and_ambiguity(self, query):
        pc = desktop.Desktop()
        with patch.object(pc, 'launch', return_value='abertura solicitada') as launch:
            self.assertEqual(pc.open_app('chrome'), 'abertura solicitada')
            launch.assert_called_once_with({'name': 'Google Chrome', 'id': 'Chrome'})
            launch.reset_mock()
            text = pc.open_app('editor')
            self.assertIn('Editor Alpha', text)
            self.assertIn('Editor Beta', text)
            launch.assert_not_called()
            pc.open_choice(2)
            launch.assert_called_once_with({'name': 'Editor Beta', 'id': 'Editor.B'})
            self.assertIn('Não encontrei', pc.open_app('inexistente'))
        query.assert_called_once_with('apps')

    @patch('desktop.query_windows', return_value={'Name': 'Discord', 'AppID': 'Discord.App'})
    def test_single_app_and_catalog_launch(self, query):
        pc = desktop.Desktop()
        pc.refresh()
        with patch('desktop.os') as win, patch('desktop.subprocess.Popen') as popen:
            win.name = 'nt'
            win.environ = {'SystemRoot': '/Windows'}
            self.assertIn('Solicitei', pc.open_app('Discord'))
            popen.assert_called_once_with(['/Windows/explorer.exe', 'shell:AppsFolder\\Discord.App'], shell=False)
            with self.assertRaises(ValueError):
                pc.launch({'name': 'Fake', 'id': 'C:\\fake.exe'})

    def test_fixed_scripts_no_user_interpolation(self):
        with patch('desktop.os') as win, patch('desktop.subprocess.run') as run:
            win.name = 'nt'
            win.environ = {'SystemRoot': '/Windows'}
            run.return_value = Mock(returncode=0, stdout='[]', stderr='')
            self.assertEqual(desktop.query_windows('apps'), [])
            self.assertIn('Get-StartApps', run.call_args.args[0][-1])
            self.assertFalse(run.call_args.kwargs['shell'])
            run.side_effect = subprocess.TimeoutExpired('powershell', 25)
            with self.assertRaises(RuntimeError):
                desktop.query_windows('system')
        with self.assertRaises(ValueError):
            desktop.query_windows('user script')

    def test_open_command_routes_app_before_files(self):
        pc = computer.Computer()
        with patch('computer.os') as win, patch.object(pc.desktop, 'matches', return_value=[1]), \
                patch.object(pc.desktop, 'open_app', return_value='aberto') as launch, patch.object(pc, 'search') as search:
            win.name = 'nt'
            self.assertEqual(pc.handle('Yuna abra o Discord'), 'aberto')
            launch.assert_called_once_with('discord')
            search.assert_not_called()

class AgentTests(unittest.TestCase):
    def plan(self, action, query='', everywhere=False):
        return json.dumps(dict(action=action, query=query, everywhere=everywhere))

    def test_local_semantic_action(self):
        pc = Mock()
        ask = Mock(return_value=self.plan('open_app', 'Discord'))
        local_agent.interpret('Coloca o Discord pra rodar', ask, pc)
        pc.desktop.open_app.assert_called_once_with('Discord')
        self.assertEqual(ask.call_args.kwargs['schema'], local_agent.SCHEMA)

    def test_process_and_system_queries(self):
        for action, method in [('system_info', 'system_info'), ('processes', 'processes')]:
            pc = Mock()
            local_agent.interpret('Veja as informações do notebook', Mock(return_value=self.plan(action)), pc)
            getattr(pc.desktop, method).assert_called_once_with()

    def test_reject_arbitrary_commands_and_invented_apps(self):
        for value in ['not json', self.plan('powershell', 'Remove-Item'),
                      self.plan('open_app', 'PowerShell'),
                      json.dumps({'action': 'open_app', 'query': 'Discord', 'everywhere': 'false'}),
                      json.dumps({'action': 'open_app', 'query': 'Discord', 'everywhere': False, 'script': 'calc'})]:
            with self.assertRaises(ValueError):
                local_agent.validate_plan(value, 'abra o Discord')

    def test_negation_instruction_and_chat(self):
        ask, pc = Mock(), Mock()
        for text in ['não abra o Discord', 'Como eu abro o Discord?']:
            self.assertIsNone(local_agent.interpret(text, ask, pc))
        ask.assert_not_called()
        pc.assert_not_called()
        self.assertIsNone(local_agent.interpret('Oi', Mock(return_value=self.plan('chat')), pc))

    def test_unsupported_has_no_side_effect(self):
        pc = Mock()
        reply = local_agent.interpret('Apague os downloads', Mock(return_value=self.plan('unsupported')), pc)
        self.assertIn('Ainda não tenho', reply)
        self.assertEqual(pc.mock_calls, [])

    @patch('yuna.ask_model')
    def test_yuna_integration_reports_observed_result(self, ask):
        ask.return_value = self.plan('list_apps')
        pc = Mock()
        pc.handle.return_value = None
        pc.desktop.list_apps.return_value = '1. Discord'
        self.assertEqual(yuna.handle_message(Mock(), 'Quero ver os programas instalados', pc), '1. Discord')
        ask.assert_called_once()
