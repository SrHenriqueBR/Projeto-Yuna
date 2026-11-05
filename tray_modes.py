"""Estados claros para presença da Yuna na bandeja (sem ação oculta).

A bandeja não é um processo separado: enquanto o ícone existe, a Yuna
está em execução. Sair encerra o aplicativo. Nenhum modo liga câmera,
microfone, LLM, gravações ou acesso remoto automaticamente.
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class TrayPolicy:
    key: str
    title: str
    detail: str
    color: str
    timer_ms: int
    battery_ms: int | None
    usb_events: bool
    unreal_heartbeat: bool

MODES = {
    "ativa": TrayPolicy(
        "ativa", "Ativa", "Pronta para conversar • verificações autorizadas",
        "#9672f5", 200, 90_000, True, True),
    "economica": TrayPolicy(
        "economica", "Modo econômico", "Pronta no ícone • sem escuta ou USB em segundo plano",
        "#8d94a5", 1200, 300_000, False, False),
    "acompanhamento": TrayPolicy(
        "acompanhamento", "Acompanhamento leve",
        "USB, energia, bateria e RAM/disco • sem câmera, microfone ou IA",
        "#6ccbb8", 1000, 180_000, True, False),
    "pausada": TrayPolicy(
        "pausada", "Pausada", "Sem escuta, observação ou tarefas em andamento",
        "#d6a05b", 1200, None, False, False),
}

def mode_policy(name):
    if name not in MODES:
        raise ValueError("Modo de bandeja desconhecido")
    return MODES[name]

def should_observe(mode, *, windows, permission):
    return bool(windows and permission and mode_policy(mode).usb_events)

def mode_tooltip(mode, *, microphone=False, usb=False):
    state = mode_policy(mode).title
    extras = []
    if microphone and mode == "ativa":
        extras.append("microfone autorizado")
    if usb:
        extras.append("USB/energia")
    return "Yuna.app • " + state + ((" • " + " / ".join(extras)) if extras else "")
