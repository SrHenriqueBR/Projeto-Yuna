"""API local: persistência real em SQLite, limites de acesso e falhas do modelo."""
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

from yuna_web import BusyError, Conversation, WEB_CONTEXT, YunaServer


class WebTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'docs').mkdir()
        (self.root / 'docs' / 'yuna-preview.html').write_text('<h1>Yuna</h1>')
        self.engine = Mock()
        self.engine.status.return_value = {'ready': True, 'model': 'modelo-de-teste'}
        self.engine.history.return_value = []
        self.engine.reply.return_value = 'Olá! Estou pronta.'
        self.server = YunaServer(('127.0.0.1', 0), root=self.root, engine=self.engine)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join()
        self.temp.cleanup()

    def request(self, method, path, data=None, headers=None):
        client = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
        props = {'Content-Type': 'application/json', 'X-Yuna-Token': self.server.token}
        props.update(headers or {})
        body = json.dumps(data).encode() if isinstance(data, (dict, list)) else data
        client.request(method, path, body, props)
        response = client.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
        client.close()
        return result

    def test_page_status_and_history(self):
        status, headers, body = self.request('GET', '/')
        self.assertEqual(status, 200)
        self.assertIn(b'Yuna', body)
        self.assertNotIn('Access-Control-Allow-Origin', headers)
        status, _, body = self.request('GET', '/api/status')
        self.assertEqual(json.loads(body)['token'], self.server.token)
        self.assertTrue(json.loads(body)['ready'])
        self.assertEqual(self.request('GET', '/api/history')[0], 200)

    def test_no_token_external_origin_and_rebinding_are_rejected(self):
        for headers in ({'X-Yuna-Token': ''}, {'Origin': 'https://outro-site.example'},
                        {'Host': f'host-externo.example:{self.server.server_port}'}):
            self.assertEqual(self.request('POST', '/api/chat', {'message': 'oi'}, headers)[0], 403)
        self.assertEqual(self.request('GET', '/api/history', headers={'X-Yuna-Token': ''})[0], 403)
        self.engine.reply.assert_not_called()

    def test_private_paths_are_not_served(self):
        for path in ('/data/yuna.db', '/yuna.py', '/../yuna.py', '/docs/../data/yuna.db'):
            self.assertEqual(self.request('GET', path)[0], 404)

    def test_message_validation_and_success(self):
        for data in ({}, {'message': ''}, {'message': 1}, []):
            self.assertEqual(self.request('POST', '/api/chat', data)[0], 400)
        self.assertEqual(self.request('POST', '/api/chat', b'{broken')[0], 400)
        self.assertEqual(self.request('POST', '/api/chat', b'x' * 65537)[0], 413)
        self.assertEqual(self.request('POST', '/api/chat', {}, {'Content-Type': 'text/plain'})[0], 415)
        status, _, body = self.request('POST', '/api/chat', {'message': '  Olá!  '})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)['answer'], 'Olá! Estou pronta.')
        self.engine.reply.assert_called_once_with('Olá!')

    def test_model_failures_are_not_reported_as_answers(self):
        for error, status in ((RuntimeError('Abra o Ollama.'), 503), (BusyError('Aguarde.'), 409)):
            self.engine.reply.side_effect = error
            actual, _, body = self.request('POST', '/api/chat', {'message': 'Oi'})
            self.assertEqual(actual, status)
            self.assertNotIn('answer', json.loads(body))

    def test_server_cannot_be_published_on_all_interfaces(self):
        with self.assertRaises(ValueError):
            YunaServer(('0.0.0.0', 0), root=self.root)

    def test_real_memory_persists_without_running_actions_or_web_search(self):
        engine = Conversation(self.root)
        with patch('yuna.ask_model', return_value='Vamos organizar suas ideias.') as model, \
             patch('yuna.public_question_to_query') as lookup, \
             patch('yuna.handle_message') as actions:
            answer = engine.reply('Me ajude a planejar meu dia.')
        self.assertEqual(answer, 'Vamos organizar suas ideias.')
        self.assertIn(WEB_CONTEXT, model.call_args.args[0][0]['content'])
        lookup.assert_not_called(); actions.assert_not_called()
        restored = Conversation(self.root)
        self.assertEqual(restored.history()[-1]['content'], answer)
        self.assertTrue((self.root / 'data' / 'conhecimentos.json').is_file())

    def test_explicit_memory_and_concurrent_turns(self):
        engine = Conversation(self.root)
        with patch('yuna.ask_model') as model:
            answer = engine.reply('Guarde que meu gato se chama Orion.')
        self.assertIn('Guardei', answer)
        model.assert_not_called()
        engine.lock.acquire()
        try:
            with self.assertRaises(BusyError): engine.reply('Oi')
        finally:
            engine.lock.release()


if __name__ == '__main__':
    unittest.main()
