from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock
import computer

class ComputerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'Documentos').mkdir()
        (self.root / 'Documentos' / 'Currículo Henrique.pdf').write_text('teste')
        (self.root / 'node_modules').mkdir()
        (self.root / 'node_modules' / 'curriculo.txt').write_text('ignorado')
        self.pc = computer.Computer()

    def tearDown(self):
        self.temp.cleanup()

    def test_names_accents_and_exclusions(self):
        files, stats = computer.search_names('curriculo henrique', [self.root])
        self.assertEqual([p.name for p in files], ['Currículo Henrique.pdf'])
        self.assertGreater(stats['skipped'], 0)
        self.assertIsNone(stats['reason'])

    def test_budget_and_no_matches(self):
        files, stats = computer.search_names('curriculo', [self.root], max_entries=0)
        self.assertEqual(files, [])
        self.assertIsNotNone(stats['reason'])
        files, stats = computer.search_names('inexistente', [self.root])
        self.assertEqual(files, [])
        self.assertIsNone(stats['reason'])

    def test_symlink_not_traversed(self):
        try:
            (self.root / 'atalho').symlink_to(self.root / 'Documentos', target_is_directory=True)
        except OSError:
            self.skipTest('Sistema não permite criar links neste ambiente.')
        files, _ = computer.search_names('curriculo', [self.root])
        self.assertEqual(len(files), 1)

    def test_unreadable_and_cancel(self):
        with patch('computer.os.scandir', side_effect=PermissionError()):
            files, stats = computer.search_names('curriculo', [self.root])
        self.assertEqual(stats['skipped'], 1)
        with patch('computer.os.scandir', side_effect=KeyboardInterrupt()):
            files, stats = computer.search_names('curriculo', [self.root])
        self.assertEqual(stats['reason'], 'cancelada pelo usuário')

    def test_natural_requests(self):
        with patch.object(self.pc, 'search', return_value='resultados') as search:
            self.assertEqual(self.pc.handle('Yuna, procure meu currículo em todo o computador'), 'resultados')
            search.assert_called_once_with('curriculo', True)
            self.pc.handle('abra meu currículo')
            search.assert_called_with('curriculo')
            self.assertIsNone(self.pc.handle('não abra meu currículo'))
            self.assertIsNone(self.pc.handle('como procurar arquivos?'))
        with patch.object(self.pc, 'open_result', return_value='ok') as launch:
            self.pc.handle('Yuna, abra o resultado 2')
            launch.assert_called_once_with(2)
            self.pc.handle('abra o primeiro')
            launch.assert_called_with(1)

    def test_open_selection_missing_and_executable(self):
        document = self.root / 'Documentos' / 'Currículo Henrique.pdf'
        executable = self.root / 'setup.exe'
        executable.write_text('not a real executable')
        self.pc.results = [document, executable]
        with patch('computer.os') as win:
            win.name = 'nt'
            self.assertIn('Solicitei', self.pc.open_result(1))
            win.startfile.assert_called_once_with(str(document), 'open')
            win.startfile.reset_mock()
            self.assertIn('não é aberto', self.pc.open_result(2))
            win.startfile.assert_not_called()
            self.assertIn('Solicitei', self.pc.open_result(2, locate=True))
            win.startfile.assert_called_once_with(str(self.root), 'open')
            document.unlink()
            self.assertIn('não existe', self.pc.open_result(1))
        self.assertIn('inválido', self.pc.open_result(0))
        self.assertIn('inválido', self.pc.open_result(99))

    def test_failed_search_clears_previous_results(self):
        self.pc.results = [self.root]
        with patch('computer.search_names', side_effect=ValueError('vazio')):
            with self.assertRaises(ValueError):
                self.pc.search('')
        self.assertEqual(self.pc.results, [])
