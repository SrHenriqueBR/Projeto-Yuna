"""Sinal de interrupção para tarefas cooperativas da Yuna.

O cancelamento só afeta operações que consultam o token; integrações de
áudio, fila e processos deverão chamar stop/check explicitamente.
"""
from threading import Event
import unicodedata


def _fold(value):
    value = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(ch for ch in value if not unicodedata.combining(ch)).casefold().strip()


STOP_PHRASES = frozenset({"break080111", "yuna parar agora", "yuna emergencia"})


def is_stop_request(text):
    return _fold(text) in STOP_PHRASES


class EmergencyStop:
    def __init__(self):
        self._stopped = Event()

    def stop(self):
        self._stopped.set()

    def reset(self):
        self._stopped.clear()

    @property
    def stopped(self):
        return self._stopped.is_set()

    def check(self):
        if self.stopped:
            raise InterruptedError("Operação cancelada pelo usuário.")
