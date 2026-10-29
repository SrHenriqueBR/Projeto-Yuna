"""Ponte local, unidirecional e opcional: Yuna Desktop -> avatar VRM.

Somente snapshots validados de animação saem para o navegador local.
Não expõe conversa, áudio, memórias, arquivos, credenciais nem comandos.
Requer token aleatório e Origin exata de http://127.0.0.1:5173.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
import secrets
import threading
from urllib.parse import quote, urlsplit

from avatar_state import HAIR, EYES, OUTFITS, HAIR_STYLES, COSTUMES, ACCESSORIES

ALLOWED_ORIGIN = "http://127.0.0.1:5173"
RESOURCE_PATH = "/v1/avatar-state"
MAX_SNAPSHOT_BYTES = 1024

_SUPPORTED_POSES = frozenset((
    "idle", "happy", "curious", "surprised", "shy", "wave",
    "talk", "wink", "laugh", "sit", "walk", "sleepy", "angry", "pose"
))
_SUPPORTED_EMOTIONS = frozenset((
    "neutral", "happy", "shy", "sad", "surprised", "annoyed"
))


def _safe_level(value):
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return 0.0
    if not (0 <= number <= 1):
        return 0.0
    return number


def _safe_appearance(value):
    """Somente enums de aparência; nenhuma informação pessoal é exposta."""
    if not isinstance(value, dict):
        return {}
    allowed = {
        "hair": HAIR, "eyes": EYES, "outfit": OUTFITS,
        "hair_style": HAIR_STYLES, "costume": COSTUMES,
        "accessory": ACCESSORIES,
    }
    return {
        name: value[name] for name, choices in allowed.items()
        if isinstance(value.get(name), str) and value[name] in choices
    }


_BATTERY_MODES = frozenset(("critical", "low", "tired", "normal",
                            "charging", "full"))


def _safe_battery(value):
    if not isinstance(value, dict):
        return None
    percent = value.get("percent")
    plugged = value.get("plugged")
    mode = value.get("mode")
    if (type(percent) is not int or not 0 <= percent <= 100
            or type(plugged) is not bool or mode not in _BATTERY_MODES):
        return None
    return {"percent": percent, "plugged": plugged, "mode": mode}


def public_snapshot(snapshot, *, revision=0, gesture_seq=0,
                    has_amplitude=False, appearance=None,
                    appearance_revision=0, battery=None):
    """Whitelisting explícito: nunca serializar uma dataclass arbitrária."""
    pose = getattr(snapshot, "pose", "idle")
    emotion = getattr(snapshot, "emotion", "neutral")
    speaking = getattr(snapshot, "speaking", False) is True
    return {
        "revision": int(revision),
        "gesture_seq": int(gesture_seq),
        "pose": pose if pose in _SUPPORTED_POSES else "idle",
        "emotion": emotion if emotion in _SUPPORTED_EMOTIONS else "neutral",
        "speaking": speaking,
        "mouth_level": _safe_level(getattr(snapshot, "mouth_level", 0)) if speaking else 0,
        "has_amplitude": bool(has_amplitude) if speaking else False,
        "appearance": _safe_appearance(appearance),
        "appearance_revision": int(appearance_revision),
        "battery": _safe_battery(battery),
    }


class Avatar3DBridge:
    def __init__(self, *, origin=ALLOWED_ORIGIN):
        if origin != ALLOWED_ORIGIN:
            raise ValueError("A ponte 3D permite apenas a origem local configurada")
        self._origin = origin
        self._token = secrets.token_urlsafe(32)
        self._lock = threading.Lock()
        self._revision = 0
        self._gesture_seq = 0
        self._appearance = {}
        self._appearance_revision = 0
        self._battery = None
        self._snapshot = public_snapshot(None)
        self._server = None
        self._thread = None

    @property
    def port(self):
        if self._server is None:
            raise RuntimeError("Ponte 3D desligada")
        return self._server.server_port

    def viewer_url(self):
        """Token só no fragmento; não será enviado na requisição inicial ao Vite."""
        return (self._origin + "/#bridgePort=" + str(self.port)
                + "&bridgeToken=" + quote(self._token, safe=""))

    def publish(self, snapshot, *, event=None, has_amplitude=False,
                appearance=None, battery=None):
        """Chamado pelo thread principal Qt; o servidor só lê este estado."""
        with self._lock:
            self._revision += 1
            if event in ("avatar.pose", "avatar.emotion"):
                self._gesture_seq += 1
            if appearance is not None:
                safe = _safe_appearance(appearance)
                if safe != self._appearance:
                    self._appearance = safe
                    self._appearance_revision += 1
            if battery is not None:
                self._battery = _safe_battery(battery)
            self._snapshot = public_snapshot(
                snapshot, revision=self._revision, gesture_seq=self._gesture_seq,
                has_amplitude=has_amplitude,
                appearance=self._appearance,
                appearance_revision=self._appearance_revision,
                battery=self._battery,
            )

    def start(self):
        if self._server is not None:
            return self
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                # URLs e tokens não são gravados em arquivos/logs.
                return

            def _origin_allowed(self):
                return self.headers.get("Origin") == owner._origin

            def _host_allowed(self):
                return self.headers.get("Host") == ("127.0.0.1:" + str(owner.port))

            def _reply(self, code, body=b"", *, cors=False):
                self.send_response(code)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Content-Length", str(len(body)))
                if cors:
                    self.send_header("Access-Control-Allow-Origin", owner._origin)
                    self.send_header("Vary", "Origin")
                self.end_headers()
                if self.command != "HEAD" and body:
                    self.wfile.write(body)

            def do_OPTIONS(self):
                if (self.path != RESOURCE_PATH or not self._origin_allowed()
                        or not self._host_allowed()
                        or self.headers.get("Access-Control-Request-Method") != "GET"
                        or "x-yuna-token" not in
                        self.headers.get("Access-Control-Request-Headers", "").lower()):
                    self._reply(403)
                    return
                self.send_response(204)
                self.send_header("Access-Control-Allow-Origin", owner._origin)
                self.send_header("Access-Control-Allow-Methods", "GET")
                self.send_header("Access-Control-Allow-Headers", "X-Yuna-Token")
                self.send_header("Access-Control-Max-Age", "60")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", "0")
                self.end_headers()

            def do_GET(self):
                if self.path != RESOURCE_PATH:
                    self._reply(404)
                    return
                if (not self._origin_allowed() or not self._host_allowed()
                        or self.client_address[0] != "127.0.0.1"):
                    self._reply(403)
                    return
                secret = self.headers.get("X-Yuna-Token", "")
                if not isinstance(secret, str) or not hmac.compare_digest(secret, owner._token):
                    self._reply(403, cors=True)
                    return
                with owner._lock:
                    payload = json.dumps(
                        owner._snapshot, separators=(",", ":")
                    ).encode("utf-8")
                if len(payload) > MAX_SNAPSHOT_BYTES:
                    self._reply(500, cors=True)
                else:
                    self._reply(200, payload, cors=True)

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._server.daemon_threads = True
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="YunaAvatar3DReadOnly", daemon=True
        )
        self._thread.start()
        return self

    def stop(self):
        if self._server is None:
            return
        server = self._server
        server.shutdown()
        server.server_close()
        self._server = None
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        self._thread = None
