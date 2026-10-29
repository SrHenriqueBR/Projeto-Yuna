"""Leitura local da bateria e comportamento ilustrativo da Yuna.

Não consulta rede, não lê aplicações e não altera energia do computador.
A personagem usa a carga *real* como contexto para animações fictícias.
"""
import ctypes
from dataclasses import dataclass
import sys
import time


class _SystemPowerStatus(ctypes.Structure):
    _fields_ = [
        ("ACLineStatus", ctypes.c_ubyte),
        ("BatteryFlag", ctypes.c_ubyte),
        ("BatteryLifePercent", ctypes.c_ubyte),
        ("SystemStatusFlag", ctypes.c_ubyte),
        ("BatteryLifeTime", ctypes.c_uint32),
        ("BatteryFullLifeTime", ctypes.c_uint32),
    ]


@dataclass(frozen=True)
class BatteryStatus:
    percent: int
    plugged: bool

    def __post_init__(self):
        if type(self.percent) is not int or not 0 <= self.percent <= 100:
            raise ValueError("Percentual de bateria inválido")
        if type(self.plugged) is not bool:
            raise ValueError("Estado de carregador inválido")


def read_battery():
    """Windows GetSystemPowerStatus: None em desktop/sem sensor ou dados incertos."""
    if sys.platform != "win32":
        return None
    try:
        state = _SystemPowerStatus()
        if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(state)):
            return None
        if (state.BatteryFlag & 128 or state.BatteryFlag == 255 or
                state.ACLineStatus not in (0, 1) or
                state.BatteryLifePercent == 255 or
                state.BatteryLifePercent > 100):
            return None
        return BatteryStatus(int(state.BatteryLifePercent),
                             plugged=bool(state.ACLineStatus))
    except (AttributeError, OSError, TypeError, ValueError):
        return None


@dataclass(frozen=True)
class BatteryMood:
    mode: str
    percent: int | None
    plugged: bool | None
    pose: str
    seek_charger: bool
    announcement: str
    suggested_activity: bool
    fps_cap: int | None


def classify(status):
    """Retorna um modo determinístico; no AC não dispara alerta de carga baixa."""
    if status is None:
        return "unavailable"
    if not isinstance(status, BatteryStatus):
        raise TypeError("Estado de bateria não suportado")
    if status.percent == 100:
        return "full"
    if status.plugged:
        return "charging"
    if status.percent <= 10:
        return "critical"
    if status.percent <= 20:
        return "low"
    if status.percent <= 35:
        return "tired"
    return "normal"


class BatteryCompanion:
    """Mensagens ocasionais com transição de estado, sem repetição compulsiva."""

    _MESSAGES = {
        "critical": "Bateria em {percent}%. Estou quase sem energia! Pode conectar o carregador?",
        "low": "Bateria em {percent}%. Vamos procurar um carregador?",
        "tired": "Bateria em {percent}%. Estou ficando sonolenta... Zzz",
        "charging": "Carregador conectado! Vou recuperar energia. ⚡",
        "full": "100% de bateria! Estou animada! Quer fazer algo comigo?",
    }

    _POSES = {
        "critical": "sleepy", "low": "sleepy", "tired": "sit",
        "charging": "sit", "full": "happy", "normal": "idle",
        "unavailable": "idle"
    }

    def __init__(self, cooldown_seconds=1200):
        self._previous_mode = "unavailable"
        self._last_by_mode = {}
        self._cooldown = max(0, float(cooldown_seconds))

    def observe(self, status, *, now=None):
        mode = classify(status)
        moment = time.monotonic() if now is None else float(now)
        changed = mode != self._previous_mode
        # Uma sessão pode começar já em bateria baixa: avisar uma vez.
        eligible = (mode in self._MESSAGES and changed
                    and moment - self._last_by_mode.get(mode, float("-inf"))
                    >= self._cooldown)
        message = (
            self._MESSAGES[mode].format(percent=status.percent)
            if eligible else ""
        )
        if message:
            self._last_by_mode[mode] = moment
        self._previous_mode = mode
        return BatteryMood(
            mode=mode,
            percent=status.percent if status is not None else None,
            plugged=status.plugged if status is not None else None,
            pose=self._POSES[mode],
            seek_charger=mode in ("low", "critical"),
            announcement=message,
            suggested_activity=mode == "full" and bool(message),
            fps_cap=12 if mode in ("low", "critical") else None,
        )


def public_battery(mood):
    """Campos numéricos e enums suficientes para o renderer 3D."""
    if mood is None or mood.percent is None:
        return None
    return {
        "percent": mood.percent,
        "plugged": mood.plugged,
        "mode": mood.mode,
    }
