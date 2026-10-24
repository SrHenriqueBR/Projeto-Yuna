import unittest
from unittest.mock import patch, Mock
import computer
import yuna

class SteamTests(unittest.TestCase):
    def test_app_requests_do_not_search_files(self):
        pc = computer.Computer()
        with patch('computer.open_steam', return_value='Steam solicitada') as launch, patch.object(pc, 'search') as search:
            for text in ['Yuna abra a steam', 'Yuna, abre pra mim a Steam',
                         '/abrir steam', 'pode abrir a Steam?', 'abra o aplicativo Steam']:
                self.assertEqual(pc.handle(text), 'Steam solicitada')
            self.assertEqual(launch.call_count, 5)
            search.assert_not_called()

    def test_negative_and_extra_instructions_never_launch_steam(self):
        pc = computer.Computer()
        with patch('computer.open_steam') as launch, patch.object(pc, 'search'):
            for text in ['não abra a steam', 'como abrir a steam?',
                         'abra a steam e instale um jogo', '/abrir steam; calc.exe']:
                pc.handle(text)
            launch.assert_not_called()

    def test_actual_screenshot_folder_phrase(self):
        self.assertEqual(yuna.parse_action('Yuna abra pra min a pasta documentos'), 'documentos')
        self.assertEqual(yuna.parse_action('abra para mim os downloads'), 'downloads')
        self.assertIsNone(yuna.parse_action('não abra pra mim os downloads'))
        with patch('yuna.open_folder', return_value='documentos solicitados') as folder:
            with patch('computer.open_steam') as steam:
                result = yuna.handle_message(Mock(), 'Yuna abra pra min a pasta documentos', computer.Computer())
                self.assertEqual(result, 'documentos solicitados')
                folder.assert_called_once_with('documentos')
                steam.assert_not_called()

    def test_fixed_uri_and_failure(self):
        with patch('computer.os') as win:
            win.name = 'nt'
            self.assertIn('Solicitei', computer.open_steam())
            win.startfile.assert_called_once_with('steam://open/main', 'open')
            win.startfile.side_effect = OSError('sem associação')
            self.assertIn('Não consegui', computer.open_steam())
            win.name = 'posix'
            self.assertIn('somente no Windows', computer.open_steam())
