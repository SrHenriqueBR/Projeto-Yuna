"""Aparência e comandos naturais do avatar 2D da Yuna.

Somente preferências visuais são persistidas em data/avatar_yuna.json.
Nenhum arquivo de memória ou de personagem original é modificado.
"""
import json
import re
from pathlib import Path
from tempfile import NamedTemporaryFile
import unicodedata

HAIR = {"preto": "#181428", "branco": "#eae5f6",
        "ruivo": "#c94f41", "roxo": "#7653a7"}
EYES = {"vermelhos": "#d9566b", "azuis": "#5eb0e8",
        "dourados": "#e9b75e", "roxos": "#ab85df"}
OUTFITS = {"escura": "#40304f", "clara": "#b39acd"}
DEFAULTS = {"hair": "preto", "eyes": "vermelhos", "outfit": "escura",
            "walking": True}


def simplified(value):
    value = unicodedata.normalize("NFKD", str(value).casefold())
    return "".join(ch for ch in value if not unicodedata.combining(ch))


def validated(data):
    if not isinstance(data, dict):
        return dict(DEFAULTS)
    result = dict(DEFAULTS)
    for key, choices in (("hair", HAIR), ("eyes", EYES), ("outfit", OUTFITS)):
        choice = data.get(key)
        if isinstance(choice, str) and choice in choices:
            result[key] = choice
    if type(data.get("walking")) is bool:
        result["walking"] = data["walking"]
    return result


def load_style(root):
    path = Path(root) / "data" / "avatar_yuna.json"
    try:
        return validated(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return dict(DEFAULTS)


def save_style(root, style):
    """Escrita atômica e localizada; sem sobrescrever assets ou memórias."""
    path = Path(root) / "data" / "avatar_yuna.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(mode="w", encoding="utf-8",
                            dir=path.parent, suffix=".tmp", delete=False) as f:
        tmp = Path(f.name)
        json.dump(validated(style), f, ensure_ascii=False, indent=2)
    try:
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)


def parse_avatar_request(message):
    """Só pedidos explícitos de visual/movimento; não interpreta hipóteses."""
    if not isinstance(message, str) or not 2 <= len(message) <= 350:
        return None
    value = simplified(message.strip())
    value = re.sub(r"^(?:ei|oi|ola|opa)\s+", "", value)
    value = re.sub(r"^yuna\s*[,!:]?\s*", "", value)
    value = re.sub(r"[.!?]+$", "", value).strip()
    if re.match(r"^(?:como|por que|porque|se eu|e se|nao|nunca|talvez)\b", value):
        return None
    # A intenção deve começar por um verbo inequívoco de solicitação.
    movement = {
        "senta": "sit", "sente": "sit", "senta ai": "sit",
        "fica sentada": "sit", "fique sentada": "sit",
        "fica chateada": "sit", "fique chateada": "sit",
        "levanta": "stand", "levante": "stand", "fica de pe": "stand",
        "fique de pe": "stand", "fica feliz": "happy",
        "fique feliz": "happy", "fica brava": "angry", "fique brava": "angry",
        "anda pela tela": "walk", "ande pela tela": "walk",
        "pode andar pela tela": "walk", "comeca a andar": "walk",
        "pare de andar": "stop", "para de andar": "stop",
        "fique parada": "stop",
    }
    if value in movement:
        return ("pose", movement[value])
    match = re.fullmatch(
        r"(?:muda|mude|troca|troque|deixa|deixe|coloca|coloque|"
        r"pinta|pinte)\s+(?:seu|o seu|os seus|sua|a sua|as suas|o|a|os|as)?\s*"
        r"(cabelo|cabelos|olho|olhos|roupa|vestido)\s+"
        r"(?:de|para|pra|na cor|em|com|por)?\s*"
        r"(preto|branco|ruivo|roxo|vermelhos|azuis|dourados|roxos|"
        r"escura|clara|vermelho|azul|dourado|roxa|preta|branca|ruiva)",
        value
    )
    if not match:
        return None
    element, chosen = match.groups()
    if element.startswith("cabelo"):
        key = "hair"
        aliases = {"preta": "preto", "ruiva": "ruivo",
                   "branca": "branco", "roxa": "roxo"}
        chosen = aliases.get(chosen, chosen)
        if chosen not in HAIR:
            return None
    elif element.startswith("olho"):
        key = "eyes"
        aliases = {"vermelho": "vermelhos", "azul": "azuis",
                   "dourado": "dourados", "roxo": "roxos"}
        chosen = aliases.get(chosen, chosen)
        if chosen not in EYES:
            return None
    else:
        key = "outfit"
        aliases = {"preta": "escura", "preto": "escura",
                   "branco": "clara", "branca": "clara"}
        chosen = aliases.get(chosen, chosen)
        if chosen not in OUTFITS:
            return None
    return ("appearance", key, chosen)


def apply_avatar_request(root, request):
    if request is None:
        return None
    style = load_style(root)
    if request[0] == "appearance":
        _, name, chosen = request
        style[name] = chosen
        save_style(root, style)
        thing = {"hair": "cabelo", "eyes": "olhos", "outfit": "roupa"}[name]
        return f"Feito, Kaizen! Mudei meu {thing} para {chosen}. 🖤"
    action = request[1]
    if action in ("walk", "stop"):
        style["walking"] = action == "walk"
        save_style(root, style)
        return ("Vou passear um pouco pela área de trabalho! 🖤" if action == "walk"
                else "Certo! Vou ficar paradinha por enquanto.")
    return {
        "sit": "Prontinho, vou me sentar um pouco. 🖤",
        "stand": "Levantei! Estou pronta para conversar.",
        "angry": "Grrr! Ativei minha expressão brava. 😤",
        "happy": "Hehe! Ativei minha expressão feliz! 🖤",
    }[action]
