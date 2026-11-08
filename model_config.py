"""Seleção persistente de modelos locais; Qwen3.5:4b é o novo padrão."""
from pathlib import Path
import os
from tempfile import NamedTemporaryFile

# Seleções anteriores explícitas continuam disponíveis.
LEGACY_MODEL = "qwen2.5:3b"
DEFAULT_MODEL = "qwen3.5:4b"
LIGHT_MODEL = "qwen2.5:1.5b"

# Modelos Qwen3.5 de inferência LOCAL, disponíveis no Ollama.
QWEN_LIGHT_MODEL = "qwen3.5:2b"
QWEN_RECOMMENDED_MODEL = "qwen3.5:4b"
QWEN_ADVANCED_MODEL = "qwen3.5:9b"

# Lista explícita: não incluir tags ":cloud" ou modelos de APIs pagas.
INSTALLER_MODELS = (
    QWEN_LIGHT_MODEL, QWEN_RECOMMENDED_MODEL, QWEN_ADVANCED_MODEL,
    LIGHT_MODEL, LEGACY_MODEL,
)
MODEL_OPTIONS = (
    (QWEN_LIGHT_MODEL, "Leve 2B · 8 GB", "≈2,7–3,1 GB de download; uso leve"),
    (QWEN_RECOMMENDED_MODEL, "Recomendado 4B", "≈3,3–4 GB de download; bom equilíbrio"),
    (QWEN_ADVANCED_MODEL, "Avançado 9B", "≈6,6–7,6 GB; mais memória e processamento"),
)
LEGACY_OPTIONS = (
    (LIGHT_MODEL, "Anterior leve 1.5B"),
    (LEGACY_MODEL, "Anterior padrão 3B"),
)
CONFIG_NAME = "modelo_yuna.txt"


def recommend_model(total_ram_gb):
    """Escolha sugerida, sem instalar ou trocar automaticamente.

    RAM total não inclui VRAM; Qwen 9B é opção manual por depender
    fortemente de GPU, memória disponível e tamanho do contexto.
    """
    try:
        gb = float(total_ram_gb)
    except (TypeError, ValueError, OverflowError):
        return QWEN_RECOMMENDED_MODEL
    if 0 < gb <= 8.5:
        return QWEN_LIGHT_MODEL
    return QWEN_RECOMMENDED_MODEL


def model_path(root):
    return Path(root) / "data" / CONFIG_NAME


def load_selected_model(root, environ=None):
    """YUNA_MODEL manual > seleção persistida válida > Qwen3.5:4b.

    O modelo manual ainda é permitido para usuários avançados, mas
    não pode escolher uma tag remota/"cloud" involuntariamente.
    """
    env = os.environ if environ is None else environ
    manual = str(env.get("YUNA_MODEL", "")).strip()
    if manual:
        if "cloud" in manual.lower():
            raise ValueError("Modelos em nuvem não são permitidos nesta configuração.")
        return manual
    try:
        selected = model_path(root).read_text(encoding="utf-8-sig").strip()
        if selected in INSTALLER_MODELS:
            return selected
    except (OSError, UnicodeError):
        pass
    return DEFAULT_MODEL


def save_selected_model(root, model):
    """Grava apenas modelos locais conhecidos, sem tocar no SQLite pessoal."""
    if model not in INSTALLER_MODELS:
        raise ValueError("Modelo não suportado pelo instalador ou não é local.")
    target = model_path(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=target.parent,
                            prefix="modelo_", suffix=".tmp", delete=False) as f:
        temp = Path(f.name)
        f.write(model + "\n")
    try:
        temp.replace(target)
    finally:
        temp.unlink(missing_ok=True)
    return target
