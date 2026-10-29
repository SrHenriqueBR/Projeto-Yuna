"""Controlador de eventos do avatar Yuna: estado puro, sem Qt e sem I/O.

Renderizadores 2D/3D podem consumir snapshots sem acesso a ferramentas ou memória.
"""
from dataclasses import dataclass, replace
import math

POSES = frozenset(("idle", "walk", "sit", "sleepy", "wave", "wink",
                   "laugh", "shy", "curious", "angry", "happy", "surprised", "pose", "talk"))
EMOTIONS = frozenset(("neutral", "happy", "shy", "sad", "surprised", "annoyed"))


@dataclass(frozen=True)
class AvatarSnapshot:
    pose: str = "idle"
    emotion: str = "neutral"
    intensity: float = 0.0
    speaking: bool = False
    mouth_level: float = 0.0
    speech_id: str = ""
    position_ms: int = 0


class AvatarController:
    """Aceita eventos validados e rejeita áudio atrasado ou fora de ordem."""

    def __init__(self):
        self._state = AvatarSnapshot()
        self._last_sequence = -1

    @property
    def snapshot(self):
        return self._state

    def dispatch(self, event, *, sequence, **data):
        if not isinstance(sequence, int) or isinstance(sequence, bool):
            raise ValueError("Sequência inválida")
        if sequence <= self._last_sequence:
            return False
        if event == "avatar.pose":
            pose = data.get("pose")
            if pose not in POSES:
                raise ValueError("Pose inválida")
            next_state = replace(self._state, pose=pose)
        elif event == "avatar.emotion":
            emotion = data.get("emotion")
            intensity = _level(data.get("intensity", 1.0))
            if emotion not in EMOTIONS:
                raise ValueError("Emoção inválida")
            next_state = replace(self._state, emotion=emotion, intensity=intensity)
        elif event == "speech.started":
            speech_id = data.get("speech_id")
            if not isinstance(speech_id, str) or not speech_id.strip() or len(speech_id) > 128:
                raise ValueError("Identificador de áudio inválido")
            next_state = replace(self._state, speaking=True, speech_id=speech_id,
                                 mouth_level=0.0, position_ms=0)
        elif event in ("speech.level", "speech.ended", "speech.interrupted"):
            if not self._state.speaking or data.get("speech_id") != self._state.speech_id:
                return False
            if event == "speech.level":
                position = data.get("position_ms")
                if not isinstance(position, int) or isinstance(position, bool) or position < self._state.position_ms:
                    return False
                next_state = replace(self._state, mouth_level=_level(data.get("amplitude")),
                                     position_ms=position)
            else:
                next_state = replace(self._state, speaking=False, mouth_level=0.0,
                                     speech_id="", position_ms=0)
        else:
            raise ValueError("Evento desconhecido")
        self._state = next_state
        self._last_sequence = sequence
        return True


def _level(value):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
        raise ValueError("Intensidade inválida")
    return max(0.0, min(1.0, float(value)))
