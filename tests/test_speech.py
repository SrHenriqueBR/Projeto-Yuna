import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yuna


class SpeechTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.memory = yuna.Memory(Path(self.temp.name) / 'yuna.db')

    def tearDown(self):
        self.memory.close()
        self.temp.cleanup()

    def test_known_errors(self):
        for text in ['Vou pode entender.', 'Sou Kaizen quem me criou.',
                     'Estou animado!', 'Obrigado, Kaizen.']:
            with self.subTest(text=text):
                self.assertTrue(yuna.speech_issue(text))

    def test_valid_language_and_quoted_examples(self):
        for text in ['Vou poder ajudar amanhã.', 'Obrigada! Estou pronta.',
                     'Você está animado?', 'Ele ficou confuso.',
                     'Você escreveu: "Estou animado".', '`Sou Kaizen`',
                     '> Estou pronto.\nEssa foi a frase dele.']:
            with self.subTest(text=text):
                self.assertFalse(yuna.speech_issue(text))

    def test_history_filter_preserves_database_and_pair_budget(self):
        self.memory.save_turn('Oi', 'Vou pode entender.')
        self.memory.save_turn('Olá', 'Olá, Kaizen!')
        before = self.memory.history()
        self.assertEqual(yuna.conversation_history(self.memory), before[-2:])
        self.assertEqual(yuna.conversation_history(self.memory, budget=1), [])
        self.assertEqual(self.memory.history(), before)

    @patch('yuna.public_question_to_query', return_value=None)
    def test_revision_saves_only_corrected_response(self, query):
        with patch('yuna.ask_model', side_effect=['Estou pronto.', 'Estou pronta.']) as model:
            self.assertEqual(yuna.respond(self.memory, 'Pode ajudar?'), 'Estou pronta.')
        self.assertEqual(model.call_count, 2)
        self.assertEqual(self.memory.history()[-1]['content'], 'Estou pronta.')

    @patch('yuna.public_question_to_query', return_value=None)
    def test_failed_revision_has_bounded_fallback(self, query):
        for failure in ['Sou Kaizen.', RuntimeError('offline')]:
            with patch('yuna.ask_model', side_effect=['Vou pode ajudar.', failure]) as model:
                answer = yuna.respond(self.memory, 'Oi')
            self.assertEqual(model.call_count, 2)
            self.assertIn('fiquei confusa', answer)
            self.assertFalse(yuna.speech_issue(answer))

    @patch('yuna.public_question_to_query', return_value=None)
    def test_normal_answer_and_no_generated_reflections_in_prompt(self, query):
        self.memory.affect.save_reflection('REFLEXAO_QUE_NAO_E_FATO')
        with patch('yuna.ask_model', return_value='Obrigada, Kaizen!') as model:
            self.assertEqual(yuna.respond(self.memory, 'Oi'), 'Obrigada, Kaizen!')
        model.assert_called_once()
        prompt = model.call_args.args[0][0]['content']
        self.assertNotIn('REFLEXAO_QUE_NAO_E_FATO', prompt)
        self.assertIn('você é Yuna', prompt)


if __name__ == '__main__':
    unittest.main()
