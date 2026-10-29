"""Microexpressões visuais discretas do avatar em repouso.

Sem IA, microfone, câmera, telemetria ou aleatoriedade global. Os gestos
são cosméticos, não simulam sentimentos ou consciência reais.
"""


def idle_expression(tick, *, speaking=False, reduced_motion=False, busy=False):
    """Retorna uma expressão curta ou None; tick é contador de animação."""
    if reduced_motion or speaking or busy:
        return None
    try:
        tick = int(tick)
    except (TypeError, ValueError, OverflowError):
        return None
    if tick < 0:
        return None
    cycle = tick % 720
    if 160 <= cycle < 177:
        return "curious"
    if 340 <= cycle < 357:
        return "happy"
    if 530 <= cycle < 545:
        return "shy"
    return None
