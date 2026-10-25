"""Iniciativa espontânea com limite de frequência e respeito a trabalho ativo.

Apenas agenda CONVITES para atividades já implementadas. A agenda não usa
internet, não grava arquivos, não lê tela nem controla programas.
"""
from dataclasses import dataclass

MINUTES_BEFORE_FIRST = 12
MINUTES_BETWEEN_NOTICES = 45
MAX_NOTICES_PER_SESSION = 3
MIN_SYSTEM_IDLE_SECONDS = 90


@dataclass
class NudgeSchedule:
    started_at: float
    last_user_action: float
    last_notice_at: float | None = None
    notices: int = 0

    @classmethod
    def start(cls, now):
        return cls(started_at=float(now), last_user_action=float(now))

    def user_active(self, now):
        self.last_user_action = float(now)

    def ready(self, now, idle_seconds=None, *, enabled=True, busy=False, pending=False):
        if not enabled or busy or pending or self.notices >= MAX_NOTICES_PER_SESSION:
            return False
        now = float(now)
        if now - self.started_at < MINUTES_BEFORE_FIRST * 60:
            return False
        if now - self.last_user_action < MINUTES_BEFORE_FIRST * 60:
            return False
        if (self.last_notice_at is not None
                and now - self.last_notice_at < MINUTES_BETWEEN_NOTICES * 60):
            return False
        if idle_seconds is not None and idle_seconds < MIN_SYSTEM_IDLE_SECONDS:
            return False
        return True

    def mark_notice(self, now):
        self.last_notice_at = float(now)
        self.notices += 1


def system_idle_seconds():
    """Tempo desde o último teclado/mouse no Windows, sem registrar entradas."""
    import os
    if os.name != "nt":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        class LastInputInfo(ctypes.Structure):
            _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]

        info = LastInputInfo()
        info.cbSize = ctypes.sizeof(LastInputInfo)
        if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
            return None
        current = ctypes.windll.kernel32.GetTickCount() & 0xFFFFFFFF
        return ((current - info.dwTime) & 0xFFFFFFFF) / 1000.0
    except (AttributeError, OSError, ValueError):
        return None


def spontaneous_enabled(initiative):
    # O usuário pediu que a Yuna fosse mais ativa; pode desativar a qualquer momento.
    return initiative._get("spontaneous_enabled", "1") == "1"


def set_spontaneous(initiative, enabled):
    initiative._set("spontaneous_enabled", "1" if enabled else "0")
    if not enabled:
        initiative._set("own_activity_pending", "")
