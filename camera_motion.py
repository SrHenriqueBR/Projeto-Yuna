"""Detecção leve de mudança visual, sem biometria, reconhecimento ou gravação.

O observador recebe apenas bytes de uma miniatura cinza 64 x 36 criada
em memória. Não sabe o que se moveu; mudanças de luz também causam alerta.
"""
import math
import time

WIDTH = 64
HEIGHT = 36
BLOCK_SIZE = WIDTH * HEIGHT


class MotionChangeDetector:
    def __init__(self, *, difference_threshold=28.0,
                 affected_ratio=0.16, required=3, cooldown_seconds=180):
        if not 0 < difference_threshold <= 255:
            raise ValueError("Diferença inválida")
        if not 0 < affected_ratio <= 1:
            raise ValueError("Proporção inválida")
        self.difference_threshold = float(difference_threshold)
        self.affected_ratio = float(affected_ratio)
        self.required = max(2, int(required))
        self.cooldown = max(0.0, float(cooldown_seconds))
        self._previous = None
        self._hits = 0
        self._last_alert = float("-inf")

    def reset(self):
        self._previous = None
        self._hits = 0

    def observe(self, grayscale_bytes, *, now=None):
        if not isinstance(grayscale_bytes, bytes) or len(grayscale_bytes) != BLOCK_SIZE:
            raise ValueError("Apenas miniamostras grayscale 64x36 são aceitas")
        previous = self._previous
        self._previous = grayscale_bytes
        if previous is None:
            return False
        changed = sum(
            abs(a - b) >= self.difference_threshold
            for a, b in zip(previous, grayscale_bytes)
        )
        if changed / BLOCK_SIZE >= self.affected_ratio:
            self._hits += 1
        else:
            self._hits = 0
        moment = time.monotonic() if now is None else float(now)
        if self._hits >= self.required and moment - self._last_alert >= self.cooldown:
            self._last_alert = moment
            self._hits = 0
            return True
        return False
