"""Testes locais sem Qt, web externo nem bibliotecas adicionais."""
from dataclasses import dataclass
import json
import unittest
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request, urlopen

from avatar3d_bridge import (
    ALLOWED_ORIGIN, RESOURCE_PATH, Avatar3DBridge, public_snapshot
)


@dataclass
class TestSnapshot:
    pose: str = "happy"
    emotion: str = "happy"
    mouth_level: float = 0.73
    speaking: bool = True
    secret_password: str = "nao-pode-sair"
    transcript: str = "conteudo da conversa confidencial"


class BridgeTests(unittest.TestCase):
    def test_whitelist_never_serializes_transcripts(self):
        state = public_snapshot(TestSnapshot(), revision=3, gesture_seq=2,
                                has_amplitude=True)
        self.assertEqual(state["pose"], "happy")
        self.assertTrue(state["has_amplitude"])
        self.assertEqual(state["mouth_level"], .73)
        self.assertEqual(state["revision"], 3)
        self.assertNotIn("secret_password", str(state))
        self.assertNotIn("conteudo", str(state))

    def test_silence_on_stop_and_invalid_levels(self):
        state = TestSnapshot(speaking=False)
        self.assertEqual(public_snapshot(state)["mouth_level"], 0)
        self.assertFalse(public_snapshot(state)["has_amplitude"])
        state.speaking = True
        state.mouth_level = float("nan")
        self.assertEqual(public_snapshot(state)["mouth_level"], 0)

    def test_http_requires_local_origin_and_random_token(self):
        bridge = Avatar3DBridge().start()
        try:
            base = "http://127.0.0.1:" + str(bridge.port)
            parts = urlsplit(bridge.viewer_url())
            secret = parse_qs(parts.fragment)["bridgeToken"][0]
            self.assertNotIn(secret, base)
            self.assertEqual(parts.hostname, "127.0.0.1")
            bridge.publish(TestSnapshot(), event="avatar.pose", has_amplitude=True)

            def make_request(origin=ALLOWED_ORIGIN, token=secret):
                return Request(
                    base + RESOURCE_PATH,
                    headers={"Origin": origin, "X-Yuna-Token": token},
                )

            with urlopen(make_request(), timeout=3) as response:
                data = json.load(response)
                self.assertEqual(response.headers.get("Cache-Control"), "no-store")
                self.assertEqual(response.headers.get("Access-Control-Allow-Origin"),
                                 ALLOWED_ORIGIN)
            self.assertEqual(data["gesture_seq"], 1)
            self.assertEqual(data["mouth_level"], .73)
            self.assertNotIn("transcript", data)

            with self.assertRaises(HTTPError) as invalid_token:
                urlopen(make_request(token="incorrect"), timeout=3)
            self.assertEqual(invalid_token.exception.code, 403)

            with self.assertRaises(HTTPError) as invalid_origin:
                urlopen(make_request(origin="https://example.com"), timeout=3)
            self.assertEqual(invalid_origin.exception.code, 403)

            with self.assertRaises(HTTPError) as missing_token:
                urlopen(Request(base + RESOURCE_PATH,
                                headers={"Origin": ALLOWED_ORIGIN}), timeout=3)
            self.assertEqual(missing_token.exception.code, 403)

            with self.assertRaises(HTTPError) as wrong_path:
                urlopen(Request(base + "/private",
                                headers={"Origin": ALLOWED_ORIGIN,
                                         "X-Yuna-Token": secret}), timeout=3)
            self.assertEqual(wrong_path.exception.code, 404)
        finally:
            bridge.stop()

    def test_preflight_allows_only_expected_origin_and_header(self):
        bridge = Avatar3DBridge().start()
        try:
            uri = "http://127.0.0.1:" + str(bridge.port) + RESOURCE_PATH
            request = Request(uri, method="OPTIONS", headers={
                "Origin": ALLOWED_ORIGIN,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "x-yuna-token"
            })
            with urlopen(request, timeout=3) as response:
                self.assertEqual(response.status, 204)
                self.assertEqual(response.headers["Access-Control-Allow-Headers"],
                                 "X-Yuna-Token")
            forbidden = Request(uri, method="OPTIONS", headers={
                "Origin": "http://evil.example",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "x-yuna-token"
            })
            with self.assertRaises(HTTPError) as denied:
                urlopen(forbidden, timeout=3)
            self.assertEqual(denied.exception.code, 403)
        finally:
            bridge.stop()

    def test_visual_preferences_are_whitelisted_and_revisioned(self):
        from avatar3d_bridge import public_snapshot
        state = TestSnapshot()
        raw = {
            "hair": "branco", "eyes": "roxos",
            "hair_style": "rabo", "costume": "casaco",
            "api_token": "never-send-this",
            "accessory": "<script>",
        }
        checked = public_snapshot(
            state, appearance=raw, appearance_revision=4)
        self.assertEqual(checked["appearance"]["hair"], "branco")
        self.assertEqual(checked["appearance"]["hair_style"], "rabo")
        self.assertNotIn("api_token", checked["appearance"])
        self.assertNotIn("accessory", checked["appearance"])
        self.assertEqual(checked["appearance_revision"], 4)

        bridge = Avatar3DBridge().start()
        try:
            bridge.publish(state, event="avatar.pose", appearance=raw)
            initial = bridge._snapshot
            self.assertEqual(initial["appearance_revision"], 1)
            self.assertEqual(initial["appearance"]["costume"], "casaco")
            # Audio events must preserve appearance without rereading disk.
            bridge.publish(state, event="speech.started")
            self.assertEqual(bridge._snapshot["appearance_revision"], 1)
            self.assertEqual(bridge._snapshot["appearance"], initial["appearance"])
            bridge.publish(state, event="avatar.pose", appearance={
                **raw, "hair": "ruivo"
            })
            self.assertEqual(bridge._snapshot["appearance_revision"], 2)
        finally:
            bridge.stop()

    def test_no_server_before_start(self):
        bridge = Avatar3DBridge()
        with self.assertRaises(RuntimeError):
            bridge.viewer_url()
        bridge.stop()

    def test_rejects_nonlocal_origin_configuration(self):
        with self.assertRaises(ValueError):
            Avatar3DBridge(origin="https://attacker.example")

if __name__ == "__main__":
    unittest.main()
