"""Consulta de chat IDs segura, sem acesso externo nos testes."""
import json
import unittest
from urllib.error import HTTPError

from configurar_alertas_telegram import list_private_chat_ids
from free_telegram_alerts import TelegramConfigurationError

TOKEN = "123456789:" + "x"*35


class StubResponse:
    def __init__(self, content):
        self.body = json.dumps(content).encode("utf-8")
    def __enter__(self):
        return self
    def __exit__(self, *_args):
        return False
    def read(self, size):
        return self.body[:size]


class ChatIdDiscoveryTests(unittest.TestCase):
    def test_private_only_and_no_token_leaked(self):
        def api(request, timeout):
            self.assertEqual(timeout, 8)
            self.assertEqual(request.get_method(), "GET")
            self.assertTrue(request.full_url.startswith(
                "https://api.telegram.org/bot"))
            return StubResponse({"ok": True, "result": [
                {"message": {"chat": {"type": "private", "id": 411222333}}},
                {"message": {"chat": {"type": "group", "id": -100112233}}},
                {"channel_post": {"chat": {"type": "channel", "id": -999}}},
                {"message": {"chat": {"type": "private", "id": 411222333}}},
                {"message": {"chat": {"type": "private", "id": 788111222}}},
            ]})
        self.assertEqual(
            list_private_chat_ids(TOKEN, opener=api),
            [411222333, 788111222]
        )

    def test_malformed_data_and_rejected_token_are_safe(self):
        with self.assertRaises(TelegramConfigurationError):
            list_private_chat_ids("INVALID", opener=lambda *_a, **_k:
                                  self.fail("network must not start"))
        for payload in ({"ok": False}, {"ok": True, "result": None}):
            with self.subTest(payload=payload), self.assertRaises(RuntimeError):
                list_private_chat_ids(
                    TOKEN, opener=lambda *_a, **_k: StubResponse(payload)
                )

    def test_http_failure_never_prints_token(self):
        def rejected(req, timeout):
            raise HTTPError(req.full_url, 403, TOKEN, {}, None)
        with self.assertRaises(RuntimeError) as context:
            list_private_chat_ids(TOKEN, opener=rejected)
        self.assertNotIn(TOKEN, str(context.exception))
