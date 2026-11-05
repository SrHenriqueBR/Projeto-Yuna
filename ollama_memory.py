"""Gerenciamento voluntário da memória do Ollama local.

Nunca encerra o serviço, exclui modelos, altera a escolha do usuário
ou faz qualquer chamada para a nuvem. O desligamento de um modelo
ocorre apenas após confirmação explícita na UI.
"""
import json

from app_tools import local_api


def _read_json(path, payload=None, *, timeout=10):
    with local_api(path, payload, timeout=timeout) as response:
        raw = response.read(1_000_001)
    if len(raw) > 1_000_000:
        raise ValueError("Resposta do Ollama maior que o limite.")
    result = json.loads(raw)
    if not isinstance(result, dict):
        raise ValueError("Resposta inválida do Ollama.")
    return result


def loaded_models():
    result = _read_json("/api/ps")
    items = result.get("models", [])
    if not isinstance(items, list) or len(items) > 100:
        raise ValueError("Lista de modelos inválida.")
    models = []
    for item in items:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if not isinstance(name, str) or not name or len(name) > 140:
            continue
        models.append({
            "name": name,
            "size": item.get("size") if isinstance(item.get("size"), int) else 0,
            "size_vram": item.get("size_vram") if isinstance(item.get("size_vram"), int) else 0,
        })
    return models


def loaded_model_status():
    models = loaded_models()
    if not models:
        return ("Nenhum modelo carregado na memória do Ollama.\n"
                "Isso não significa que os modelos foram desinstalados.")
    lines = ["Modelos carregados no Ollama (valores informados pelo serviço):"]
    for item in models[:20]:
        mb = item["size"] / 1024**3
        gpu = item["size_vram"] / 1024**3
        lines.append(f"• {item['name']}: {mb:.2f} GiB totais / {gpu:.2f} GiB VRAM")
    lines.append("Para liberar RAM/VRAM, escolha o nome na Central e confirme a ação.")
    return "\n".join(lines)


def unload_model(name):
    """Remove da memória somente um modelo listado em /api/ps nesta chamada."""
    if not isinstance(name, str) or len(name) > 140:
        raise ValueError("Nome de modelo inválido.")
    names = {item["name"] for item in loaded_models()}
    if name not in names:
        raise ValueError("Esse modelo não está carregado; não fiz alterações.")
    result = _read_json(
        "/api/generate",
        {"model": name, "prompt": "", "stream": False, "keep_alive": 0},
        timeout=30,
    )
    if result.get("error") or result.get("done") is not True:
        raise RuntimeError("O Ollama não confirmou a liberação do modelo.")
    return (f"Solicitei ao Ollama descarregar {name} da memória.\n"
            "O modelo continua instalado no disco, e será carregado "
            "novamente se uma conversa precisar dele. A liberação real "
            "depende do serviço e de tarefas simultâneas.")
