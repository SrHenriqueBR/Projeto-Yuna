"""Convites de vídeo por Magi1020, sem acesso automático à webcam.

Este comando NÃO é senha, token de autenticação nem autorização de câmera.
A chamada acontece em um serviço externo, aberto somente após um clique
explícito. A outra pessoa precisa entrar e liberar sua câmera no navegador.
"""
import re
import secrets
import unicodedata
from urllib.parse import urlsplit


EXTERNAL_MEETING_SERVICE = "https://meet.jit.si"
ROOM_PREFIX = "YunaVisita-"
ROOM_BYTES = 24  # 192 bits de aleatoriedade por convite
_ROOM = re.compile(r"YunaVisita-[A-Za-z0-9_-]{32}\Z")
_MAX_LINK_LENGTH = 200


def is_magi_camera_request(text):
    """Somente comando isolado; mencionar 'Magi1020' em conversa não ativa nada."""
    if not isinstance(text, str) or len(text) > 80:
        return False
    normalized = unicodedata.normalize("NFKD", text)
    normalized = "".join(
        char for char in normalized if not unicodedata.combining(char)
    ).casefold().strip()
    return bool(re.fullmatch(r"(?:yuna[, :]+)?magi1020[.!]?", normalized))


def new_remote_camera_invite():
    """Cria link novo e não o salva, envia, abre ou registra em logs."""
    name = ROOM_PREFIX + secrets.token_urlsafe(ROOM_BYTES)
    return EXTERNAL_MEETING_SERVICE + "/" + name


def validate_remote_camera_invite(value):
    """Permite só convites Yuna deste domínio e caminho, sem redirecionamentos."""
    if not isinstance(value, str) or not 1 <= len(value) <= _MAX_LINK_LENGTH:
        raise ValueError("Convite inválido. Cole o link Magi1020 completo.")
    url = value.strip()
    if any(ord(char) < 33 or ord(char) == 127 for char in url):
        raise ValueError("Convite inválido. Cole o link Magi1020 completo.")
    try:
        parts = urlsplit(url)
        if (parts.scheme != "https" or parts.hostname != "meet.jit.si"
                or parts.netloc != "meet.jit.si"
                or parts.username is not None or parts.password is not None
                or parts.query or parts.fragment or not parts.path.startswith("/")):
            raise ValueError("Esse não é um convite Magi1020 válido.")
        room = parts.path[1:]
        if not _ROOM.fullmatch(room):
            raise ValueError("Esse não é um convite Magi1020 válido.")
    except (ValueError, TypeError):
        raise ValueError("Esse não é um convite Magi1020 válido.") from None
    return url
