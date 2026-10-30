"""Perfis explícitos de inferência; não troca ou baixa modelos."""
import json
from pathlib import Path
from tempfile import NamedTemporaryFile

PROFILES = {
    "equilibrado": {"num_ctx": 8192, "num_predict": 768, "keep_alive": "2m"},
    "rapido": {"num_ctx": 8192, "num_predict": 384, "keep_alive": "5m"},
}


def profile_path(root):
    return Path(root) / "data" / "desempenho_yuna.json"


def load_profile(root):
    try:
        value = json.loads(profile_path(root).read_text(encoding="utf-8"))
        return value if isinstance(value, str) and value in PROFILES else "equilibrado"
    except (OSError, ValueError, UnicodeError):
        return "equilibrado"


def save_profile(root, name):
    if name not in PROFILES:
        raise ValueError("Escolha rapido ou equilibrado.")
    path = profile_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as file:
        temporary = Path(file.name)
        file.write(json.dumps(name) + "\n")
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def options_for(root, purpose="conversation"):
    if purpose not in ("conversation", "code"):
        raise ValueError("Finalidade de inferência desconhecida.")
    profile = dict(PROFILES[load_profile(root)])
    if purpose == "code":
        # Código precisa caber em JSON completo, mesmo no perfil de fala curta.
        profile.update(num_ctx=12288, num_predict=3072)
    return profile


def handle_performance(message, root):
    value = message.strip().casefold()
    if value.split(" ", 1)[0] != "/desempenho":
        return None
    parts = value.split()
    if len(parts) == 2:
        save_profile(root, parts[1])
    elif len(parts) != 1:
        raise ValueError("Use /desempenho rapido ou /desempenho equilibrado.")
    name = load_profile(root)
    selected = PROFILES[name]
    return (f"Perfil de conversa: {name}. Limite de saída: {selected['num_predict']} tokens. "
            f"Modelo mantido em memória por até {selected['keep_alive']} após uma resposta.\n"
            "O perfil rapido favorece respostas curtas e usa RAM por mais tempo. "
            "A velocidade depende do seu hardware; não acelera programas externos. "
            "Não troco o modelo nem instalo programas. Para reverter: /desempenho equilibrado.")
