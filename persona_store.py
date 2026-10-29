"""Preferências locais de apresentação por conta do sistema operacional.

Não identifica pessoas pela voz. Arquivos separados por identificador hash da
conta do Windows: duas pessoas usando a mesma conta compartilham preferências.
"""
import getpass
import hashlib
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from persona_preferences import PersonaPreferences


def preference_path(root, account=None):
    if account is None:
        account = os.environ.get("USERDOMAIN", "") + "\\" + getpass.getuser()
    if not isinstance(account, str) or not account.strip():
        raise ValueError("Conta local inválida")
    key = hashlib.sha256(account.casefold().encode("utf-8")).hexdigest()[:24]
    return Path(root) / "data" / "personas" / (key + ".json")


def load_preferences(root, account=None):
    """Um arquivo ausente/corrompido nunca impede iniciar o aplicativo."""
    default = PersonaPreferences()
    try:
        with preference_path(root, account).open("r", encoding="utf-8") as fp:
            content = fp.read(4097)
        if len(content) > 4096:
            return default
        data = json.loads(content)
        if not isinstance(data, dict) or data.get("schema") != 1:
            return default
        return default.updated(
            presentation=data["presentation"],
            voice_style=data["voice_style"],
            display_name=data["display_name"],
        )
    except (OSError, ValueError, TypeError, KeyError, UnicodeError):
        return default


def save_preferences(root, preferences, account=None):
    """Grava somente campos permitidos; nunca toca nas memórias SQLite."""
    if not isinstance(preferences, PersonaPreferences):
        raise TypeError("Preferências inválidas")
    checked = PersonaPreferences().updated(
        presentation=preferences.presentation,
        voice_style=preferences.voice_style,
        display_name=preferences.display_name,
    )
    target = preference_path(root, account)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({
        "schema": 1,
        "presentation": checked.presentation,
        "voice_style": checked.voice_style,
        "display_name": checked.display_name,
    }, ensure_ascii=False)
    with NamedTemporaryFile("w", encoding="utf-8", dir=target.parent,
                            prefix="persona_", suffix=".tmp", delete=False) as fp:
        temporary = Path(fp.name)
        fp.write(payload + "\n")
    try:
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    return target
