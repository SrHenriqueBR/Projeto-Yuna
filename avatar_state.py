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
HAIR_STYLES = {"longo": "Cabelo longo", "curto": "Cabelo curto",
               "marias": "Maria-chiquinhas", "rabo": "Rabo de cavalo"}
COSTUMES = {"vestido": "Vestido gótico", "casual": "Roupa casual",
            "casaco": "Casaco de inverno"}
ACCESSORIES = {"laco": "Laço", "tiara": "Tiara", "oculos": "Óculos",
               "nenhum": "Sem acessório"}
SIZES = {"pequena": 0.75, "normal": 1.0, "grande": 1.30}
DEFAULTS = {"hair": "preto", "eyes": "vermelhos", "outfit": "escura",
            "hair_style": "longo", "costume": "vestido", "accessory": "laco",
            "size": "normal", "walking": True, "reduced_motion": False}


def simplified(value):
    value = unicodedata.normalize("NFKD", str(value).casefold())
    return "".join(ch for ch in value if not unicodedata.combining(ch))


def validated(data):
    if not isinstance(data, dict):
        return dict(DEFAULTS)
    result = dict(DEFAULTS)
    for key, choices in (("hair", HAIR), ("eyes", EYES), ("outfit", OUTFITS),
                         ("hair_style", HAIR_STYLES), ("costume", COSTUMES),
                         ("accessory", ACCESSORIES), ("size", SIZES)):
        choice = data.get(key)
        if isinstance(choice, str) and choice in choices:
            result[key] = choice
    for setting in ("walking", "reduced_motion"):
        if type(data.get(setting)) is bool:
            result[setting] = data[setting]
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
        "acena": "wave", "acene": "wave", "da tchau": "wave",
        "de tchau": "wave", "acena para mim": "wave",
        "acena pra mim": "wave", "me da tchau": "wave",
        "faz pose": "pose", "faca pose": "pose",
        "faz uma pose": "pose", "faca uma pose": "pose",
        "fica surpresa": "surprised", "fique surpresa": "surprised",
        "pisca": "wink", "pisca pra mim": "wink", "pisca para mim": "wink",
        "da uma piscadinha": "wink", "me da uma piscadinha": "wink",
        "da risada": "laugh", "de risada": "laugh", "ri pra mim": "laugh",
        "ri para mim": "laugh",
        "fica curiosa": "curious", "fique curiosa": "curious",
        "faz cara de curiosa": "curious", "mostra curiosidade": "curious",
        "fica timida": "shy", "fique timida": "shy",
        "fica envergonhada": "shy", "fique envergonhada": "shy",
        "dorme": "sleepy", "vai dormir": "sleepy",
        "tira uma soneca": "sleepy", "faca uma soneca": "sleepy",
        "acorda": "wake", "acorde": "wake", "desperta": "wake",
    }
    if value in movement:
        return ("pose", movement[value])

    # Preferência de acessibilidade; somente ordens curtas e explícitas.
    motion_settings = {
        "reduz as animacoes": True,
        "reduza as animacoes": True,
        "diminui as animacoes": True,
        "diminua as animacoes": True,
        "ativa movimento reduzido": True,
        "ative movimento reduzido": True,
        "desliga as animacoes": True,
        "desligue as animacoes": True,
        "volta com as animacoes": False,
        "retoma as animacoes": False,
        "retome as animacoes": False,
        "ativa as animacoes": False,
        "ative as animacoes": False,
        "permite movimentos": False,
        "permita movimentos": False,
    }
    if value in motion_settings:
        return ("motion", motion_settings[value])

    # Tamanho do avatar: opções explícitas, sem confundir com a janela de chat.
    if re.fullmatch(
            r"(?:fica|fique|deixa|deixe|torna|torne) (?:voce |vc |o avatar )?"
            r"(pequena|pequeno|normal|grande)", value):
        chosen = value.rsplit(" ", 1)[1]
        return ("appearance", "size", {"pequeno": "pequena"}.get(chosen, chosen))
    size = re.fullmatch(
        r"(?:muda|mude|ajusta|ajuste|troca|troque|coloca|coloque|deixa|deixe) "
        r"(?:o |seu )?(?:tamanho|avatar) (?:para|pra|em) "
        r"(pequeno|pequena|normal|grande)", value
    )
    if size:
        return ("appearance", "size", {"pequeno": "pequena"}.get(size[1], size[1]))

    # Mudanças explícitas de estilo: não confundir cor do cabelo com corte.
    if re.fullmatch(r"(?:faz|faca|coloca|coloque) (?:duas )?"
                    r"(?:maria-chiquinhas|maria chiquinhas|marias chiquinhas)",
                    value):
        return ("appearance", "hair_style", "marias")
    if re.fullmatch(r"(?:prende|prenda|muda|mude|coloca|coloque|deixa|deixe) "
                    r"(?:o |seu )?cabelo (?:em |num |no |pra |para )?"
                    r"(?:um )?rabo de cavalo", value):
        return ("appearance", "hair_style", "rabo")
    cut = re.fullmatch(
        r"(?:muda|mude|deixa|deixe|corta|corte|troca|troque) "
        r"(?:o |seu )?cabelo (?:para |pra |bem |mais )?"
        r"(curto|longo)", value)
    if cut:
        return ("appearance", "hair_style", cut[1])
    garment = re.fullmatch(
        r"(?:usa|use|veste|vista|coloca|coloque|troca|troque|muda|mude) "
        r"(?:a |uma |o |um |sua |seu |roupa para |roupa pra )?"
        r"(vestido(?: gotico)?|casaco(?: de inverno)?|roupa casual|"
        r"visual casual|jaqueta)", value)
    if garment:
        item = garment[1]
        style = ("casaco" if "casaco" in item or item == "jaqueta" else
                 "casual" if "casual" in item else "vestido")
        return ("appearance", "costume", style)
    add = re.fullmatch(
        r"(?:coloca|coloque|usa|use|bota|ponha|poe) "
        r"(?:um |uma |o |a )?(laco|tiara|oculos)", value
    )
    if add:
        return ("appearance", "accessory", add[1])
    remove = re.fullmatch(
        r"(?:tira|tire|remove|remova) "
        r"(?:o |a |os |as )?(?:laco|tiara|oculos|acessorio|acessorios)", value
    )
    if remove:
        return ("appearance", "accessory", "nenhum")

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
    if request[0] == "motion":
        style["reduced_motion"] = request[1]
        save_style(root, style)
        return ("Vou ficar mais paradinha e reduzir as animações. 🖤"
                if request[1] else
                "Voltei a animar meus movimentos suaves! 🖤")
    if request[0] == "appearance":
        _, name, chosen = request
        style[name] = chosen
        save_style(root, style)
        if name == "size":
            return {
                "pequena": "Prontinho! Agora fiquei menorzinha. 🖤",
                "normal": "Voltei para meu tamanho normal. 🖤",
                "grande": "Pronto, Kaizen! Agora estou maior na tela. 🖤",
            }[chosen]
        if name == "hair_style":
            return f"Prontinho! Meu cabelo agora está no estilo {HAIR_STYLES[chosen].lower()}. 🖤"
        if name == "costume":
            return f"Troquei de roupa! Agora estou com {COSTUMES[chosen].lower()}. 🖤"
        if name == "accessory":
            return ("Tirei o acessório do cabelo e do rosto. 🖤"
                    if chosen == "nenhum" else
                    f"Coloquei {ACCESSORIES[chosen].lower()} no meu visual. 🖤")
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
        "wave": "Oieee! Estou acenando para você! 👋",
        "pose": "Ta-dã! Fiz uma pose de anime! ✨",
        "surprised": "Uau! Ativei minha expressão de surpresa! ✨",
        "wink": "Hihi! Uma piscadinha de anime pra você, Kaizen! 😉",
        "laugh": "Hahaha! Olha só minha risada! 🖤",
        "shy": "E-ei! Ativei meu jeitinho tímido... ✨",
        "sleepy": "Vou tirar uma sonequinha aqui na tela... Zzz 🖤",
        "wake": "Acordei! Já estou prontinha de novo. 🖤",
    }[action]
