"""Sem chamadas de rede reais: valida custos, conteúdo e proteção de dados."""
import json
import unittest
from urllib.error import HTTPError

from free_alert_budget import AlertBudget, MAX_ALERT_ATTEMPTS_PER_SESSION
from free_telegram_alerts import (
    FreeTelegramNotifier, TelegramConfigurationError, TelegramSendError,
    validate_bot_token, validate_private_chat_id,
)

TOKEN = "123456789:" + "X" * 35
CHAT = "123456789"


class FakeTelegramResponse:
    def __init__(self, result):
        self.content = json.dumps(result).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, size):
        return self.content[:size]


class TelegramTransportTests(unittest.TestCase):
    def test_api_request_is_free_mode_and_contains_only_fixed_event(self):
        captured = []

        def fake_open(request, timeout):
            self.assertEqual(timeout, 8)
            self.assertEqual(request.get_method(), "POST")
            self.assertTrue(request.full_url.startswith(
                "https://api.telegram.org/bot"))
            captured.append(json.loads(request.data.decode("utf-8")))
            return FakeTelegramResponse({"ok": True, "result": {"message_id": 100}})

        sender = FreeTelegramNotifier(TOKEN, CHAT)
        self.assertTrue(sender.send_event("sos", opener=fake_open))
        self.assertTrue(sender.send_event("som_alto", opener=fake_open))
        for body in captured:
            self.assertEqual(body["chat_id"], CHAT)
            self.assertIs(body["allow_paid_broadcast"], False)
            self.assertTrue(body["protect_content"])
            self.assertNotIn("camera", body)
            self.assertNotIn("microphone", body)
            self.assertNotIn("audio", body)
            self.assertNotIn("frame", body)
        self.assertIn("SOS", captured[0]["text"])
        self.assertIn("som alto", captured[1]["text"].lower())
        self.assertNotEqual(captured[0]["text"], captured[1]["text"])

    def test_no_arbitrary_message_or_media(self):
        sender = FreeTelegramNotifier(TOKEN, CHAT)
        for unsafe in ("screenshot", "microfone", "", None, 123):
            with self.subTest(unsafe=unsafe), self.assertRaises(ValueError):
                sender.send_event(unsafe, opener=lambda *_a, **_k:
                                  self.fail("Network called for invalid event"))

    def test_rejects_invalid_token_or_nonprivate_chat_id(self):
        for token in ("token", "Bearer 123", "123:abc", "123456789:" + "a"*10,
                      "123456789:" + "X"*40 + "/secret", None):
            with self.subTest(token=token), self.assertRaises(TelegramConfigurationError):
                validate_bot_token(token)
        for chat_id in ("-100012345", "@public_channel", "123abc", 0,
                        12.3, "1/other", None, ""):
            with self.subTest(chat_id=chat_id), self.assertRaises(
                    TelegramConfigurationError):
                validate_private_chat_id(chat_id)
        self.assertEqual(validate_private_chat_id(CHAT), CHAT)

    def test_http_errors_never_expose_token_or_phone(self):
        sender = FreeTelegramNotifier(TOKEN, CHAT)

        def rejected(_request, timeout):
            raise HTTPError(
                "https://api.telegram.org/bot" + TOKEN + "/sendMessage",
                403, "TOKEN " + TOKEN, None, None,
            )

        with self.assertRaises(TelegramSendError) as received:
            sender.send_event("sos", opener=rejected)
        self.assertNotIn(TOKEN, str(received.exception))
        self.assertNotIn(CHAT, str(received.exception))

    def test_server_must_confirm_accepted_message(self):
        sender = FreeTelegramNotifier(TOKEN, CHAT)
        for response in (
            {"ok": False, "description": "token secret"},
            {"ok": True, "result": {}},
            {"ok": True, "result": {"message_id": "not-an-integer"}},
        ):
            with self.subTest(response=response), self.assertRaises(
                    TelegramSendError):
                sender.send_event(
                    "sos", opener=lambda *_a, **_k: FakeTelegramResponse(response)
                )


class AlertBudgetTests(unittest.TestCase):
    def test_sos_and_sound_have_separate_cooldowns(self):
        budget = AlertBudget()
        self.assertTrue(budget.reserve("sos", now=100))
        self.assertFalse(budget.reserve("sos", now=110))
        self.assertTrue(budget.reserve("som_alto", now=110))
        self.assertFalse(budget.reserve("som_alto", now=399))
        self.assertTrue(budget.reserve("sos", now=146))
        self.assertTrue(budget.reserve("som_alto", now=411))
        self.assertEqual(budget.remaining, MAX_ALERT_ATTEMPTS_PER_SESSION - 4)

    def test_limit_prevents_more_than_six_attempts(self):
        budget = AlertBudget()
        for i in range(MAX_ALERT_ATTEMPTS_PER_SESSION):
            self.assertTrue(budget.reserve("sos", now=i*50))
        self.assertFalse(budget.reserve("sos", now=999))
        self.assertEqual(budget.remaining, 0)
        with self.assertRaises(ValueError):
            budget.reserve("unknown", now=1000)
        self.assertFalse(budget.reserve("sos", now=float("nan")))

if __name__ == "__main__":
    unittest.main()
