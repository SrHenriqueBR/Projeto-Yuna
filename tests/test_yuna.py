import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from io import BytesIO
import urllib.error
import yuna

class BaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'yuna.db'
        self.memory = yuna.Memory(self.path)

    def tearDown(self):
        self.memory.close()
        self.tmp.cleanup()

    def test_restart_and_delete(self):
        self.memory.remember('Prefiro voz feminina.')
        self.memory.save_turn('Olá', 'Oi!')
        self.memory.close()
        self.memory = yuna.Memory(self.path)
        self.assertEqual(self.memory.history()[0]['content'], 'Olá')
        self.assertEqual(len(self.memory.facts()), 1)
        self.memory.clear()
        self.assertEqual(self.memory.history(), [])
        self.assertEqual(len(self.memory.facts()), 1)
        self.assertEqual(self.memory.forget(self.memory.facts()[0][0]), 1)
        self.assertEqual(self.memory.facts(), [])
        self.memory.remember('Teste')
        self.memory.save_turn('Olá', 'Oi')
        self.memory.clear(all_data=True)
        self.assertEqual(self.memory.facts(), [])
        self.assertEqual(self.memory.history(), [])

    def test_context_is_bounded_and_ordered(self):
        for i in range(10):
            self.memory.save_turn(str(i), 'Resposta')
        history = self.memory.history()
        self.assertEqual(len(history), 12)
        self.assertEqual(history[0], {'role': 'user', 'content': '4'})
        self.assertEqual(history[-1]['role'], 'assistant')
        with self.assertRaises(ValueError):
            self.memory.remember(' ')

    def test_export_and_old_knowledge_survive_restart(self):
        self.memory.remember('Prefiro voz feminina.')
        self.memory.save_turn('Meu notebook é Alienware.', 'Entendi.')
        for i in range(8):
            self.memory.save_turn(f'Outra conversa {i}', 'Certo.')
        self.memory.close()
        self.memory = yuna.Memory(self.path)
        self.assertIn('Meu notebook é Alienware.', self.memory.recall('Qual meu notebook?'))
        data = json.loads((self.path.parent / 'conhecimentos.json').read_text(encoding='utf-8'))
        self.assertEqual(len(data['conversas']), 18)
        self.assertEqual(data['memorias'][0]['texto'], 'Prefiro voz feminina.')
        self.memory.clear(all_data=True)
        data = json.loads((self.path.parent / 'conhecimentos.json').read_text(encoding='utf-8'))
        self.assertEqual(data['conversas'], [])
        self.assertEqual(data['memorias'], [])
        self.assertEqual(self.memory.recall('notebook'), [])

    def test_export_failure_keeps_database(self):
        with patch('yuna.Path.write_text', side_effect=OSError('disco indisponível')):
            self.memory.save_turn('Meu notebook é Alienware.', 'Certo.')
        self.assertEqual(len(self.memory.history()), 2)
        self.memory.export()
        self.assertTrue((self.path.parent / 'conhecimentos.json').exists())

    @patch('yuna.urllib.request.build_opener')
    def test_request_and_atomic_persistence(self, build):
        self.memory.remember('Prefiro português.')
        build.return_value.open.return_value = BytesIO(json.dumps(
            {'message': {'content': 'Olá!'}}).encode())
        self.assertEqual(yuna.respond(self.memory, 'Oi'), 'Olá!')
        request = build.return_value.open.call_args.args[0]
        payload = json.loads(request.data)
        self.assertFalse(payload['stream'])
        self.assertIn('Prefiro português.', payload['messages'][0]['content'])
        self.assertEqual(request.full_url, 'http://127.0.0.1:11434/api/chat')
        self.assertEqual(len(self.memory.history()), 2)

    @patch('yuna.urllib.request.build_opener')
    def test_failed_requests_do_not_pollute_history(self, build):
        errors = [urllib.error.URLError('offline'), TimeoutError(),
                  urllib.error.HTTPError('url', 404, 'missing', {}, None)]
        for error in errors:
            build.return_value.open.side_effect = error
            with self.assertRaises(RuntimeError):
                yuna.respond(self.memory, 'Oi')
            self.assertEqual(self.memory.history(), [])
        build.return_value.open.side_effect = None
        for response in [b'not json', b'{}', b'{"message":{"content":""}}']:
            build.return_value.open.return_value = BytesIO(response)
            with self.assertRaises(RuntimeError):
                yuna.respond(self.memory, 'Oi')
            self.assertEqual(self.memory.history(), [])

if __name__ == '__main__':
    unittest.main()
