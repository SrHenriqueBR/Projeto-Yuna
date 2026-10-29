"""Permissão temporária para visualizar webcams e câmeras RTSP da rede local.

Apenas fontes escolhidas pelo usuário; não enumera, procura, escaneia,
grava, compartilha ou abre câmeras automaticamente.
"""
from dataclasses import dataclass
import ipaddress
import math
import re
import time
from urllib.parse import urlsplit

from emergency_stop import is_stop_request

MAX_CAMERA_SESSION_SECONDS = 600
MAX_SOURCE_LENGTH = 2048
_WEBCAM = re.compile(r"^(?:(?:webcam|camera|câmera)\s*)?([0-9])$", re.I)


@dataclass(frozen=True)
class CameraSource:
    kind: str
    index: int | None = None
    url: str | None = None

    @property
    def label(self):
        return ("Webcam " + str(self.index)) if self.kind == "webcam" else "Câmera RTSP local"


def parse_camera_source(raw):
    """Aceita webcam 0..9 ou RTSP privado. URLs/credenciais nunca são logadas."""
    if not isinstance(raw, str) or not 1 <= len(raw) <= MAX_SOURCE_LENGTH:
        raise ValueError("Informe webcam 0..9 ou uma URL RTSP da rede local")
    source = raw.strip()
    if any(ord(ch) < 32 for ch in source):
        raise ValueError("Fonte de câmera inválida")
    match = _WEBCAM.fullmatch(source)
    if match:
        return CameraSource("webcam", index=int(match.group(1)))
    try:
        uri = urlsplit(source)
        if uri.scheme.casefold() != "rtsp" or not uri.hostname:
            raise ValueError("Use uma câmera RTSP local ou webcam 0..9")
        # No primeiro piloto, nunca abrir endpoints públicos nem fazer DNS.
        host = ipaddress.ip_address(uri.hostname)
        if not (host.is_private and not host.is_loopback
                and not host.is_multicast and not host.is_unspecified
                and not host.is_link_local):
            raise ValueError("A câmera deve possuir IP privado da rede local")
        if uri.port is not None and not 1 <= uri.port <= 65535:
            raise ValueError("Porta RTSP inválida")
        if uri.fragment:
            raise ValueError("Não inclua fragmentos na URL da câmera")
        if not uri.path:
            raise ValueError("Informe o caminho do fluxo RTSP")
    except (ValueError, TypeError) as exc:
        # Nunca incluir URL/credenciais na mensagem retornada.
        if isinstance(exc, ValueError) and str(exc) in (
            "Use uma câmera RTSP local ou webcam 0..9",
            "A câmera deve possuir IP privado da rede local",
            "Porta RTSP inválida",
            "Não inclua fragmentos na URL da câmera",
            "Informe o caminho do fluxo RTSP",
        ):
            raise
        raise ValueError("A URL RTSP precisa utilizar um IP privado válido") from None
    return CameraSource("rtsp", url=source)


class CameraPermission:
    """Guarda consentimento apenas na memória desta sessão."""

    def __init__(self):
        self._source = None
        self._expires = 0.0

    def authorize(self, source, *, approved, duration_seconds=300, now=None):
        if approved is not True:
            raise PermissionError("A câmera só pode ser aberta após autorização explícita")
        if (type(duration_seconds) not in (int, float) or
                not math.isfinite(duration_seconds) or
                not 0 < duration_seconds <= MAX_CAMERA_SESSION_SECONDS):
            raise ValueError("Duração de câmera inválida")
        parsed = parse_camera_source(source)
        moment = time.monotonic() if now is None else float(now)
        self._source = parsed
        self._expires = moment + duration_seconds
        return parsed

    def check(self, *, now=None):
        moment = time.monotonic() if now is None else float(now)
        if self._source is None or moment >= self._expires:
            self.stop()
            raise PermissionError("Sessão de câmera encerrada ou expirada")
        return self._source

    def remaining(self, *, now=None):
        moment = time.monotonic() if now is None else float(now)
        return max(0.0, self._expires - moment) if self._source is not None else 0.0

    def request_stop(self, text):
        if is_stop_request(text):
            self.stop()
            return True
        return False

    def stop(self):
        self._source = None
        self._expires = 0.0
