import unittest
from unittest.mock import patch, Mock
import yuna

class ActionTests(unittest.TestCase):
    def test_requests(self):
        for text in ['Yuna, abra meus downloads', '/abrir downloads',
                     'Yuna, abra o explorador e vá até a pasta downloads',
                     'Yuna verifica o explorador abra ele e va ate a aba download',
                     'Pode abrir a pasta de downloads?', 'Abra downloads, por favor']:
            self.assertEqual(yuna.parse_action(text), 'downloads', text)
        self.assertEqual(yuna.parse_action('abra o explorador'), 'explorador')
        self.assertEqual(yuna.parse_action('Yuna, abra meus documentos'), 'documentos')

    def test_non_requests_do_not_run(self):
        for text in ['não abra downloads', 'como abrir downloads?',
                     'explique como abrir downloads', 'abra downloads e apague tudo',
                     '/abrir C:\\Windows', 'abra downloads; calc.exe',
                     'lembre que eu digo abra downloads', 'abra downloads && whoami']:
            self.assertIsNone(yuna.parse_action(text), text)

    @patch('yuna.respond')
    @patch('yuna.open_folder', return_value='Abertura solicitada.')
    def test_dispatch_without_model(self, launch, chat):
        memory = Mock()
        result = yuna.handle_message(memory, 'Yuna, abra downloads')
        self.assertEqual(result, 'Abertura solicitada.')
        launch.assert_called_once_with('downloads')
        chat.assert_not_called()
        memory.save_turn.assert_called_once()

    @patch('yuna.subprocess.Popen')
    def test_windows_arguments_and_error(self, popen):
        # Preserve host Path implementation while simulating the platform check.
        from pathlib import Path
        with patch('yuna.Path', Path), patch('yuna.os') as os_mock:
            os_mock.name = 'nt'
            os_mock.environ = {'SystemRoot': '/Windows'}
            self.assertIn('Solicitei', yuna.open_folder('downloads'))
            popen.assert_called_once_with([str(Path('/Windows') / 'explorer.exe'), 'shell:Downloads'], shell=False)
            popen.side_effect = OSError('indisponível')
            self.assertIn('Não consegui', yuna.open_folder('downloads'))
        with self.assertRaises(ValueError):
            yuna.open_folder('cmd.exe')

    @patch('yuna.subprocess.Popen')
    def test_other_platform(self, popen):
        with patch('yuna.os') as os_mock:
            os_mock.name = 'posix'
            self.assertIn('somente no Windows', yuna.open_folder('downloads'))
        popen.assert_not_called()
