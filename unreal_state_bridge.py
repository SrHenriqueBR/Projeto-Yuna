"""Ponte opcional de estado do avatar para Unreal Engine 5 (sem socket/rede).

Apenas dados públicos de animação são publicados em JSON num arquivo local.
A ponte é ativada manualmente no desktop; nunca exporta memória, documentos,
voz bruta, transcrição, comandos do computador ou segredos.
"""
import json
import math
import os
from pathlib import Path
import secrets
import tempfile
import time

from avatar3d_bridge import public_snapshot

_STATE_FILENAME = "yuna_unreal_state.json"
_MAX_BYTES = 2048
_MIN_AUDIO_PERIOD = 0.09


class UnrealStateBridge:
    def __init__(self, root, *, clock=None, monotonic=None):
        self.path = Path(root) / "data" / _STATE_FILENAME
        self._clock = clock if clock is not None else time.time
        self._monotonic = monotonic if monotonic is not None else time.monotonic
        self._enabled = False
        self._revision = 0
        self._gesture_seq = 0
        self._last_audio_write = float("-inf")
        self._session = ""

    @property
    def enabled(self):
        return self._enabled

    def start(self, snapshot=None):
        """Não lança o editor e não requer Unreal instalado."""
        if self._enabled:
            return self
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._session = secrets.token_hex(12)
        self._enabled = True
        if not self.publish(snapshot, force=True):
            self._enabled = False
            raise OSError("Não foi possível criar o estado local da Yuna Unreal")
        return self

    def publish(self, snapshot, *, event=None, has_amplitude=False, force=False):
        """Escreve apenas uma seleção fixa de campos validados, com troca atômica."""
        if not self._enabled:
            return False
        now_mono = self._monotonic()
        if (not force and event == "speech.level"
                and now_mono - self._last_audio_write < _MIN_AUDIO_PERIOD):
            return False
        self._revision += 1
        if event in ("avatar.pose", "avatar.emotion"):
            self._gesture_seq += 1
        safe = public_snapshot(
            snapshot, revision=self._revision, gesture_seq=self._gesture_seq,
            has_amplitude=has_amplitude
        )
        value = getattr(snapshot, "intensity", 0.0)
        if isinstance(value, bool) or not isinstance(value, (float, int)):
            value = 0.0
        intensity = float(value)
        if not math.isfinite(intensity):
            intensity = 0.0
        output = {
            "version": 1,
            "session": self._session,
            "updated_at": float(self._clock()),
            "revision": safe["revision"],
            "gesture_seq": safe["gesture_seq"],
            "pose": safe["pose"],
            "emotion": safe["emotion"],
            "intensity": max(0.0, min(1.0, intensity)),
            "speaking": safe["speaking"],
            "mouth_level": safe["mouth_level"],
        }
        payload = json.dumps(output, ensure_ascii=True, separators=(",", ":"))
        if len(payload.encode("utf-8")) > _MAX_BYTES:
            return False
        temp_path = None
        try:
            # NamedTemporaryFile sempre fica na mesma pasta para os.replace atômico.
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.path.parent,
                prefix=".yuna_unreal_", suffix=".tmp", delete=False
            ) as temp:
                temp_path = Path(temp.name)
                json.dump(output, temp, ensure_ascii=True, separators=(",", ":"))
            os.replace(temp_path, self.path)
            if event == "speech.level":
                self._last_audio_write = now_mono
            return True
        except OSError:
            return False
        finally:
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    pass

    def stop(self):
        """Não apaga o arquivo de outra sessão da Yuna, se existir."""
        self._enabled = False
        try:
            if self.path.stat().st_size > _MAX_BYTES:
                return
            current = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(current, dict) and current.get("session") == self._session:
                self.path.unlink(missing_ok=True)
        except (OSError, ValueError, TypeError):
            pass
        finally:
            self._session = ""
