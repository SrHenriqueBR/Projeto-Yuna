import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from yuna_governance import Governance


class GovernanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Governance(self.temp.name)
        self.password = 'Senha ficticia para teste 123'

    def tearDown(self):
        self.temp.cleanup()

    def configure(self):
        self.store.configure('Responsável de teste', self.password)
        return self.store.owner()

    def test_default_has_no_owner_and_no_shared_knowledge(self):
        self.assertIsNone(self.store.owner())
        self.assertEqual(self.store.reference_context(), '')
        with self.assertRaises(ValueError):
            self.store.propose('Uma ideia geral para estudar.', True, None)

    def test_owner_requires_password_not_a_name_and_sessions_expire(self):
        self.configure()
        with self.assertRaises(PermissionError): self.store.login('Kaizen')
        token = self.store.login(self.password)
        self.assertTrue(self.store.authenticated(token))
        self.store.sessions[token] = 0
        self.assertFalse(self.store.authenticated(token))
        with self.assertRaises(ValueError): self.configure()
        with sqlite3.connect(self.store.path) as db:
            encoded = db.execute('SELECT password_hash FROM owner').fetchone()[0]
        self.assertNotIn(self.password, encoded)

    def test_sharing_requires_exact_recipient_consent_and_no_sensitive_data(self):
        owner = self.configure()
        for consent, recipient in ((False, owner['id']), ('true', owner['id']), (True, 'outro')):
            with self.assertRaises(ValueError):
                self.store.propose('Uma ideia geral para estudar.', consent, recipient)
        with self.assertRaises(ValueError):
            self.store.propose('Minha senha é algo que não deve ser compartilhado.', True, owner['id'])
        self.assertEqual(self.store.dashboard()['proposals'], [])

    def test_approval_is_required_and_sender_can_withdraw_approved_knowledge(self):
        owner = self.configure()
        text = 'Organizar uma lista de tarefas ajuda a separar prioridades.'
        proof = self.store.propose(text, True, owner['id'])
        self.assertEqual(self.store.reference_context(), '')
        self.store.review(proof['id'], 'approved')
        self.assertIn(text, self.store.reference_context())
        with self.assertRaises(PermissionError): self.store.withdraw(proof['id'], 'sem comprovante')
        self.store.withdraw(proof['id'], proof['receipt'])
        self.assertEqual(self.store.own_status(proof['id'], proof['receipt']), 'withdrawn')
        self.assertEqual(self.store.reference_context(), '')
        self.assertEqual(self.store.dashboard()['proposals'][0]['content'], '')
        with self.assertRaises(ValueError): self.store.review(proof['id'], 'approved')
        self.assertNotIn(text, json.dumps(self.store.dashboard()['audit']))

    def test_rejected_proposal_does_not_enter_the_context(self):
        owner = self.configure()
        proof = self.store.propose('Faça pausas curtas ao organizar seus estudos.', True, owner['id'])
        self.store.review(proof['id'], 'rejected')
        self.assertEqual(self.store.reference_context(), '')
        self.assertEqual(self.store.own_status(proof['id'], proof['receipt']), 'rejected')
        self.store.failures = [__import__('time').monotonic()] * 5
        with self.assertRaises(PermissionError): self.store.login(self.password)


if __name__ == '__main__':
    unittest.main()
