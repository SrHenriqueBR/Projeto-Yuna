"""Animações suaves do avatar sem dependência do Qt.

Calcula a animação por quadro. Não consulta tela, teclado, câmera, microfone
ou arquivos. Recebe apenas a posição do cursor fornecida pelo widget Qt.
"""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class MotionFrame:
    blink: float
    eye_dx: float
    eye_dy: float
    hair_sway: float
    breath: float
    body_bob: float
    mouth_open: float
    tilt: float


def clamp(value, low, high):
    return max(low, min(high, value))


def frame_at(tick, pose, cursor=None, speaking=False, reduced_motion=False):
    """Retorna deslocamentos em pixels apropriados para um widget 190x277."""
    tick = max(0, int(tick))
    t = tick * .08

    # Pisca a cada ~4.8 s e inclui uma segunda piscada ocasional.
    cycle = tick % 60
    blink = 1.0 if cycle in (1, 2) else 0.0
    if (tick // 60) % 4 == 2 and cycle in (8, 9):
        blink = 1.0
    if pose in ("sit", "sleepy"):
        blink = max(blink, .5)

    eye_dx = eye_dy = 0.0
    if cursor is not None:
        x, y = cursor
        # Cursor tem coordenadas locais relativas ao avatar.
        eye_dx = clamp((float(x) - 95) / 31.0, -3.0, 3.0)
        eye_dy = clamp((float(y) - 135) / 51.0, -2.0, 2.0)

    if reduced_motion:
        return MotionFrame(blink, eye_dx, eye_dy, 0.0, 0.0, 0.0,
                           0.0, 0.0)

    breath = 1.6 * math.sin(t * 1.45)
    hair_sway = 3.1 * math.sin(t * 2.0) + 1.2 * math.sin(t * 3.6)
    walking = pose == "walk"
    body_bob = 2.6 * math.sin(t * 8) if walking else .8 * math.sin(t * 1.5)
    if pose == "sit":
        body_bob = .2 * math.sin(t)
    mouth_open = 0.0
    if speaking or pose == "talk":
        # A abertura acompanha o ritmo de fala de forma aproximada,
        # sem alegar sincronização fonética exata.
        mouth_open = 2.0 + 3.0 * abs(math.sin(t * 13))
    tilt = 1.6 * math.sin(t * 1.1) if pose in ("idle", "happy") else 0.0

    return MotionFrame(blink, eye_dx, eye_dy, hair_sway, breath,
                       body_bob, mouth_open, tilt)
