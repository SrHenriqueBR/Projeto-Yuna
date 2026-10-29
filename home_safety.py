"""Proteção doméstica opcional: autorização visível, eventos discretos e sem áudio bruto.

O motor não abre microfone, câmera, rede nem toca o sistema.
A sessão é criada pela pessoa que está diante do notebook e expira.
"""
from dataclasses import dataclass
import math
import re
import time

MAX_SESSION_SECONDS = 1800
SOUND_THRESHOLD_RMS = 0.28
SOUND_CONSECUTIVE_BLOCKS = 5
SOUND_QUIET_REARM_BLOCKS = 15
SOUND_ALERT_COOLDOWN = 300
SOUND_ALERT_GRACE_SECONDS = 15

CONTACT = re.compile(r"\+?[1-9][0-9]{7,14}\Z")
ALERT_KIND = frozenset(("sos", "som_alto"))


def validate_contact(number):
    """Contato informado pela pessoa monitorada; não é lido de banco ou perfil."""
    if not isinstance(number, str):
        raise ValueError("Informe o WhatsApp do contato com DDI e DDD")
    value = re.sub(r"[\s()\-]", "", number.strip())
    if not CONTACT.fullmatch(value):
        raise ValueError("Informe o número completo com DDI, sem outros caracteres")
    return value.lstrip("+")


class SafetySession:
    """Sessão local opt-in, sem persistência e com cancelamento por stop."""

    def __init__(self):
        self._contact = None
        self._audio_enabled = False
        self._expires_at = 0.0

    @property
    def active(self):
        return self._contact is not None

    @property
    def microphone_enabled(self):
        return self.active and self._audio_enabled

    def begin(self, *, approved, contact, listen_to_loud_sounds=False,
              seconds=MAX_SESSION_SECONDS, now=None):
        if approved is not True:
            raise PermissionError("A pessoa que usa o notebook deve autorizar")
        if type(listen_to_loud_sounds) is not bool:
            raise ValueError("Permissão de microfone inválida")
        if (type(seconds) not in (int, float) or not math.isfinite(seconds)
                or not 0 < seconds <= MAX_SESSION_SECONDS):
            raise ValueError("Tempo de sessão inválido")
        number = validate_contact(contact)
        moment = time.monotonic() if now is None else float(now)
        self._contact = number
        self._audio_enabled = listen_to_loud_sounds
        self._expires_at = moment + seconds
        return True

    def check(self, now=None):
        moment = time.monotonic() if now is None else float(now)
        if not self.active or moment >= self._expires_at:
            self.stop()
            raise PermissionError("A sessão de segurança expirou ou foi encerrada")
        return self._contact

    def remaining(self, now=None):
        moment = time.monotonic() if now is None else float(now)
        return max(0.0, self._expires_at - moment) if self.active else 0

    def stop(self):
        self._contact = None
        self._audio_enabled = False
        self._expires_at = 0.0


@dataclass(frozen=True)
class SafetyEvent:
    kind: str
    text: str

    def __post_init__(self):
        if self.kind not in ALERT_KIND:
            raise ValueError("Tipo de alerta não permitido")


SAFETY_EVENTS = {
    "sos": SafetyEvent("sos", "SOS manual acionado no notebook"),
    "som_alto": SafetyEvent(
        "som_alto", "Som alto detectado localmente; pode ser alarme falso"
    ),
}


class SoundLevelDetector:
    """Detecta volume alto sustentado. NÃO reconhece palavras nem perigo real.

    A função recebe somente valores RMS escalares de blocos de ~100ms,
    sem amostras de voz. Exige silêncio para rearme e cooldown.
    """

    def __init__(self, *, threshold=SOUND_THRESHOLD_RMS,
                 required=SOUND_CONSECUTIVE_BLOCKS,
                 quiet_to_rearm=SOUND_QUIET_REARM_BLOCKS,
                 cooldown_seconds=SOUND_ALERT_COOLDOWN):
        if not (0 < float(threshold) <= 1):
            raise ValueError("Limiar inválido")
        self.threshold = float(threshold)
        self.required = max(2, int(required))
        self.quiet_to_rearm = max(1, int(quiet_to_rearm))
        self.cooldown = max(0.0, float(cooldown_seconds))
        self._loud = 0
        self._quiet = 0
        self._armed = True
        self._last_alert = float("-inf")

    def observe(self, rms, *, now=None):
        if type(rms) not in (float, int) or not math.isfinite(rms):
            return False
        moment = time.monotonic() if now is None else float(now)
        if rms >= self.threshold:
            self._loud += 1
            self._quiet = 0
            if (self._armed and self._loud >= self.required
                    and moment - self._last_alert >= self.cooldown):
                self._armed = False
                self._last_alert = moment
                return True
        else:
            self._loud = 0
            self._quiet += 1
            if self._quiet >= self.quiet_to_rearm:
                self._armed = True
        return False


class AlertPending:
    """Prazo para que a pessoa cancele uma suspeita de som antes do envio."""

    def __init__(self):
        self._due = None

    def schedule(self, *, now=None, delay=SOUND_ALERT_GRACE_SECONDS):
        if self._due is not None:
            return False
        moment = time.monotonic() if now is None else float(now)
        self._due = moment + max(1, float(delay))
        return True

    def ready(self, *, now=None):
        moment = time.monotonic() if now is None else float(now)
        return self._due is not None and moment >= self._due

    @property
    def pending(self):
        return self._due is not None

    def cancel(self):
        self._due = None

    def consume_if_ready(self, *, now=None):
        if not self.ready(now=now):
            return False
        self.cancel()
        return True
