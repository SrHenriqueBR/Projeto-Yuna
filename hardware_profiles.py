"""Perfis de capacidade da Yuna, sem dependências externas ou coleta de dados.

Os perfis são recomendações de recursos, não uma garantia de desempenho.
A GPU dedicada deve ser informada pelo detector do sistema ou pelo usuário;
não se assume GPU apenas com base na RAM.
"""
from dataclasses import dataclass
import os


@dataclass(frozen=True)
class HardwareProfile:
    name: str
    model_suggestion: str
    avatar_fps: int
    renderer: str
    effects: bool
    voice_mode: str


PROFILES = {
    "leve": HardwareProfile("leve", "qwen2.5:1.5b", 12, "qt2d", False, "push_to_talk"),
    "equilibrado": HardwareProfile("equilibrado", "qwen2.5:3b", 24, "qt2d", True, "push_to_talk"),
    "avancado": HardwareProfile("avancado", "qwen2.5:3b", 30, "qt2d", True, "push_to_talk"),
}


def recommend_profile(total_ram_gb, dedicated_vram_gb=0):
    """Sugere perfil considerando RAM e VRAM; não habilita recursos ausentes."""
    try:
        ram = float(total_ram_gb)
        vram = float(dedicated_vram_gb)
    except (ValueError, TypeError):
        return PROFILES["leve"]
    if not (0 < ram < 2048 and 0 <= vram < 256):
        return PROFILES["leve"]
    if ram >= 16 and vram >= 6:
        return PROFILES["avancado"]
    if ram >= 12:
        return PROFILES["equilibrado"]
    return PROFILES["leve"]


def select_profile(total_ram_gb, dedicated_vram_gb=0, environ=None):
    """YUNA_PERFIL força o perfil quando válido; caso contrário recomenda."""
    env = os.environ if environ is None else environ
    override = env.get("YUNA_PERFIL", "").strip().casefold()
    if override in PROFILES:
        return PROFILES[override]
    return recommend_profile(total_ram_gb, dedicated_vram_gb)
