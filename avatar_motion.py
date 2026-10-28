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


def ambient_pose(tick, walking=True, reduced_motion=False):
    """Agenda calma, determinística, independente de Qt ou do modelo de IA.

    Não faz inferências sobre o humor do usuário; controla só animação local.
    Em modo reduzido, nunca desloca a janela pela área de trabalho.
    """
    if reduced_motion:
        return "idle"
    if not walking:
        return "idle"
    phase = max(0, int(tick)) % 900
    if phase < 315:
        return "walk"
    if phase < 395:
        return "idle"
    if phase < 585:
        return "walk"
    if phase < 755:
        return "sit"
    return "idle"


def ease_gaze(current, target, strength=0.18):
    """Aproxima os olhos do cursor sem salto brusco ou histórico de tela."""
    alpha = clamp(float(strength), 0.0, 1.0)
    return (
        float(current[0]) + (float(target[0]) - float(current[0])) * alpha,
        float(current[1]) + (float(target[1]) - float(current[1])) * alpha,
    )

def smoothstep(value):
    """Interpolação sem saltos de velocidade, para transições visuais."""
    x = clamp(float(value), 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def blend_frames(previous, current, progress):
    """Mistura quadros de animação sem tocar no estado do avatar."""
    weight = smoothstep(progress)
    return MotionFrame(**{
        name: getattr(previous, name) * (1.0 - weight)
              + getattr(current, name) * weight
        for name in MotionFrame.__dataclass_fields__
    })


def frame_at(tick, pose, cursor=None, speaking=False, reduced_motion=False,
             mouth_level=None):
    """Retorna deslocamentos em pixels apropriados para um widget 190x277."""
    tick = max(0, int(tick))
    t = tick * .08

    # Pisca a cada ~4.8 s e inclui uma segunda piscada ocasional.
    cycle = tick % 60
    blink = 1.0 if cycle in (1, 2) else 0.0
    if (tick // 60) % 4 == 2 and cycle in (8, 9):
        blink = 1.0
    if pose == "sleepy":
        blink = 1.0  # Duas pálpebras fechadas ao tirar uma soneca.
    elif pose == "laugh":
        blink = 1.0  # Olhos em meia-lua, desenhados pelo avatar.
    elif pose == "sit":
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
    # Oscilações de frequências diferentes evitam um balanço robótico repetitivo.
    hair_sway = (2.7 * math.sin(t * 1.7)
                 + 0.7 * math.sin(t * 3.1)
                 + 0.4 * math.sin(t * 0.48))
    if pose in ("sit", "sleepy"):
        hair_sway *= .35
    walking = pose == "walk"
    body_bob = 2.6 * math.sin(t * 8) if walking else .8 * math.sin(t * 1.5)
    if pose in ("sit", "sleepy"):
        body_bob = .2 * math.sin(t)
    mouth_open = 0.0
    if speaking:
        if mouth_level is None:
            # MP3 sem amplitude decodificada: ritmo aproximado, mas só durante
            # reprodução confirmada pelo player.
            mouth_open = 2.0 + 3.0 * abs(math.sin(t * 13))
        else:
            mouth_open = max(0.0, min(1.0, float(mouth_level))) * 6.0
    elif pose == "talk" and mouth_level is None:
        # Compatibilidade de pré-visualização; a interface não solicita
        # mais a pose 'talk' antes do áudio real.
        mouth_open = 2.0 + 3.0 * abs(math.sin(t * 13))
    tilt = (1.2 * math.sin(t * 0.8) + .4 * math.sin(t * .29)
            if pose in ("idle", "happy", "shy", "wink") else 0.0)

    return MotionFrame(blink, eye_dx, eye_dy, hair_sway, breath,
                       body_bob, mouth_open, tilt)
