"""Orçamento conservador de recursos para módulos futuros da Yuna.

Não inicia serviços, não altera modelos instalados e não aloca VRAM.
Os valores são limites de configuração iniciais, não benchmarks.
"""
from dataclasses import dataclass

from hardware_profiles import HardwareProfile, PROFILES


@dataclass(frozen=True)
class ResourceBudget:
    avatar_fps: int
    max_context_tokens: int
    background_workers: int
    allow_optional_3d: bool
    allow_advanced_effects: bool
    preferred_voice: str


_BUDGETS = {
    "leve": ResourceBudget(12, 2048, 1, False, False, "push_to_talk"),
    "equilibrado": ResourceBudget(24, 4096, 2, False, True, "push_to_talk"),
    "avancado": ResourceBudget(30, 8192, 4, True, True, "push_to_talk"),
}


def budget_for(profile):
    """Retorna limites seguros por perfil, sem ativar funcionalidades futuras."""
    name = profile.name if isinstance(profile, HardwareProfile) else profile
    if name not in PROFILES:
        raise ValueError("Perfil de hardware desconhecido")
    return _BUDGETS[name]


def constrained_budget(profile, *, battery_saver=False, reduced_motion=False):
    """Reduz o orçamento sob economia de energia/acessibilidade."""
    original = budget_for(profile)
    fps = min(original.avatar_fps, 12) if battery_saver else original.avatar_fps
    if reduced_motion:
        fps = min(fps, 12)
    return ResourceBudget(
        avatar_fps=fps,
        max_context_tokens=min(original.max_context_tokens, 4096)
        if battery_saver else original.max_context_tokens,
        background_workers=1 if battery_saver else original.background_workers,
        allow_optional_3d=original.allow_optional_3d and not battery_saver
        and not reduced_motion,
        allow_advanced_effects=original.allow_advanced_effects
        and not battery_saver and not reduced_motion,
        preferred_voice=original.preferred_voice,
    )
