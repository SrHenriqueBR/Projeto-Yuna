"""Orçamento rígido de alertas, para evitar spam e envios repetidos."""
import math
import time

from home_safety import SAFETY_EVENTS

MAX_ALERT_ATTEMPTS_PER_SESSION = 6
ALERT_INTERVALS = {"sos": 45.0, "som_alto": 300.0}


class AlertBudget:
    """Contabiliza tentativas, inclusive as que falharem; sem retries ocultos."""

    def __init__(self, max_attempts=MAX_ALERT_ATTEMPTS_PER_SESSION):
        self._remaining = max(0, min(MAX_ALERT_ATTEMPTS_PER_SESSION,
                                     int(max_attempts)))
        self._last_by_type = {}

    @property
    def remaining(self):
        return self._remaining

    def reserve(self, kind, *, now=None):
        if kind not in SAFETY_EVENTS:
            raise ValueError("Evento inválido")
        current = time.monotonic() if now is None else float(now)
        if not math.isfinite(current):
            return False
        if self._remaining == 0:
            return False
        if current - self._last_by_type.get(kind, float("-inf")) < ALERT_INTERVALS[kind]:
            return False
        self._remaining -= 1
        self._last_by_type[kind] = current
        return True
