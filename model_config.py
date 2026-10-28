"""Seleção opcional do modelo local da Yuna, sem alterar memórias antigas.

Ollama continua sendo a fonte do modelo. Arquivo local escolhido pelo instalador
tem uma allowlist curta; variável YUNA_MODEL mantém precedência para usuários avançados.
"""
from pathlib import Path
import os
from tempfile import NamedTemporaryFile

DEFAULT_MODEL = "qwen2.5:3b"
LIGHT_MODEL = "qwen2.5:1.5b"
INSTALLER_MODELS = (LIGHT_MODEL, DEFAULT_MODEL)
CONFIG_NAME = "modelo_yuna.txt"


def recommend_model(total_ram_gb):
    """Em máquinas de até 8 GB, sugere um modelo mais leve sem trocar sozinho."""
    try:
        gb = float(total_ram_gb)
    except (TypeError, ValueError):
        return DEFAULT_MODEL
    return LIGHT_MODEL if 0 < gb <= 8.5 else DEFAULT_MODEL


def model_path(root):
    return Path(root) / "data" / CONFIG_NAME


def load_selected_model(root, environ=None):
    """Variável de ambiente explícita > seleção persistida > padrão anterior."""
    env = os.environ if environ is None else environ
    manual = env.get("YUNA_MODEL", "").strip()
    if manual:
        return manual
    try:
        selected = model_path(root).read_text(encoding="utf-8-sig").strip()
        if selected in INSTALLER_MODELS:
            return selected
    except (OSError, UnicodeError):
        pass
    return DEFAULT_MODEL


def save_selected_model(root, model):
    """Grava apenas uma opção conhecida, de forma atômica, sem tocar no SQLite."""
    if model not in INSTALLER_MODELS:
        raise ValueError("Modelo não suportado pelo instalador.")
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
