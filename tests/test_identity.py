from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import yuna

class IdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'yuna.db'
        self.memory = yuna.Memory(self.path)

    def tearDown(self):
        self.memory.close()
        self.temp.cleanup()

    @patch('yuna.respond', side_effect=AssertionError('Não deve chamar o modelo'))
    def test_screenshot_sequence_and_restart(self, model):
        self.memory.remember('meu nome e Kaizen')
        self.assertEqual(yuna.handle_message(self.memory, 'Qual o meu nome?'), 'Seu nome é Kaizen.')
        self.assertIn('Guardei', yuna.handle_message(self.memory, 'Meu nome e Kaizen'))
        self.assertEqual(yuna.handle_message(self.memory, 'Seu nome e Yuna?'),
                         'Meu nome é Yuna. Sou sua assistente pessoal.')
        self.memory.close()
        self.memory = yuna.Memory(self.path)
        self.assertEqual(yuna.handle_message(self.memory, 'Sabe meu nome?'), 'Seu nome é Kaizen.')
        self.assertEqual(len(self.memory.facts()), 1)

    def test_new_name_replaces_only_names_and_deletion(self):
        self.memory.remember('Prefiro voz feminina.')
        self.memory.remember('Meu nome é Henrique')
        yuna.identity_reply(self.memory, 'Me chamo João da Silva.')
        self.assertEqual(yuna.identity_reply(self.memory, 'Qual meu nome?'), 'Seu nome é João da Silva.')
        self.assertEqual(len(self.memory.facts()), 2)
        for ident, text in self.memory.facts():
            if yuna.declared_name(text):
                self.memory.forget(ident)
        self.assertIn('Ainda não tenho', yuna.identity_reply(self.memory, 'Qual meu nome?'))

    def test_no_guess_or_role_confusion(self):
        for text in ['Meu nome é Kaizen?', 'Seu nome é Yuna', 'Meu nome é Kaizen e gosto de jogos',
                     'meu nome não é Kaizen', 'talvez meu nome é Kaizen']:
            self.assertIsNone(yuna.declared_name(text), text)
        self.assertIn('Ainda não tenho', yuna.identity_reply(self.memory, 'Sabe meu nome?'))
        yuna.identity_reply(self.memory, 'Seu nome é Yuna?')
        self.assertEqual(self.memory.facts(), [])
