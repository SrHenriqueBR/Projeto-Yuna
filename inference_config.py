"""Perfis explícitos de inferência; não troca ou baixa modelos."""
import json
import re
import unicodedata
from pathlib import Path
from tempfile import NamedTemporaryFile

PROFILES = {
    "maximo": {"num_ctx": 16384, "num_predict": 4096, "keep_alive": "5m"},
    "equilibrado": {"num_ctx": 8192, "num_predict": 768, "keep_alive": "2m"},
    "rapido": {"num_ctx": 8192, "num_predict": 384, "keep_alive": "5m"},
}


def profile_path(root):
    return Path(root) / "data" / "desempenho_yuna.json"


def load_profile(root):
    try:
        value = json.loads(profile_path(root).read_text(encoding="utf-8"))
        return value if isinstance(value, str) and value in PROFILES else "maximo"
    except (OSError, ValueError, UnicodeError):
        return "maximo"


def save_profile(root, name):
    if name not in PROFILES:
        raise ValueError("Escolha maximo, rapido ou equilibrado.")
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
        if load_profile(root) == "maximo":
            profile.update(num_ctx=16384, num_predict=8192)
        else:
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
        raise ValueError("Use /desempenho maximo, rapido ou equilibrado.")
    name = load_profile(root)
    selected = PROFILES[name]
    return (f"Perfil de conversa: {name}. Limite de saída: {selected['num_predict']} tokens. "
            f"Modelo mantido em memória por até {selected['keep_alive']} após uma resposta.\n"
            "O perfil maximo amplia respostas e código, com maior uso de RAM e tempo. "
            "O perfil rapido favorece respostas curtas. "
            "A velocidade depende do seu hardware; não acelera programas externos. "
            "Não troco o modelo nem instalo programas. Para reverter: /desempenho equilibrado.")


def request_purpose(message):
    value = "".join(c for c in unicodedata.normalize("NFKD", message.casefold())
                    if not unicodedata.combining(c))
    code = re.search(r"\b(codigo|script|funcao|algoritmo|programa|python|javascript|typescript|sql|html|css|bug|traceback)\b", value)
    request = re.search(r"\b(crie|cria|criar|gere|gera|gerar|faca|escreva|escrever|implemente|implementar|corrija|corrigir|depure|refatore|programar|otimize|analise)\b", value)
    return "code" if code and (request or "Traceback" in message or chr(96) * 3 in message) else "conversation"
