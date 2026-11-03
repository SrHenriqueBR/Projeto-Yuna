"""Intenções explícitas do modo residente; texto gerado nunca vira comando."""
import re
import unicodedata


def folded(text):
    value = unicodedata.normalize("NFKD", str(text or "")).casefold()
    return "".join(c for c in value if not unicodedata.combining(c))


def command(text):
    value = re.sub(r"\s+", " ", folded(text)).strip().rstrip(".!?")
    value = re.sub(r"^(?:ola[, ]+|oi[, ]+|ei[, ]+)?yuna[, :]+", "", value)
    value = re.sub(r"^por favor[, ]+", "", value)
    return re.sub(r"[, ]+por favor$", "", value)


def power_intent(text):
    value = command(text)
    if value in ("/desligar", "desliga o computador", "desligue o computador",
                 "desligar o computador", "desliga o pc", "desligue o notebook"):
        return "shutdown"
    if value in ("/cancelar desligamento", "cancelar desligamento",
                 "cancele o desligamento", "cancela o desligamento",
                 "nao desligue o computador", "nao desliga o computador"):
        return "cancel"
    return None


def wake_command(text):
    """Só um chamado no início da transcrição; nenhum substring dentro de conversa."""
    if not isinstance(text, str) or len(text) > 300:
        return None
    match = re.fullmatch(r"\s*(?:(?:ol[aá]|oi|ei)[,\s]+)?yuna(?:[,.!?:\s]+(.*))?",
                         text, re.IGNORECASE)
    if not match:
        return None
    rest = (match[1] or "").strip()
    return "Olá Yuna" if not rest else "Yuna " + rest


GAME_COMMANDS = {
    "pule": "jump", "pula": "jump", "pular": "jump",
    "avance": "move_forward", "avancar": "move_forward",
    "recue": "move_backward", "recuar": "move_backward",
    "esquerda": "move_left", "direita": "move_right",
    "olhe para a esquerda": "look_left", "olhe para a direita": "look_right",
    "interaja": "interact", "interagir": "interact",
    "agache": "crouch", "agachar": "crouch", "pause": "pause", "pausar": "pause",
}


def game_intent(text):
    value = command(text)
    if value in ("/jogo", "configurar jogo", "configurar controle do jogo"):
        return "configure"
    if value in ("/jogo parar", "pare o controle do jogo"):
        return "stop"
    for prefix in ("/jogo ", "no jogo "):
        if value.startswith(prefix):
            return GAME_COMMANDS.get(value[len(prefix):])
    return None


def banking_action(text):
    """Limite de produto para pedidos de ação financeira; não autentica contas."""
    value = folded(text)
    banking = re.search(r"\b(?:banc[oa]|bancari\w*|nubank|itau|bradesco|santander|"
                        r"picpay|inter bank|internet banking|pix|boleto|transferencia|"
                        r"cartao de credito|mercado pago)\b", value)
    action = re.search(r"\b(?:abr\w*|acesse?|acessar|entr\w*|pag\w*|transfir\w*|"
                       r"transferir|envie?|enviar|fa[cz]\w*|consult\w*|moviment\w*|"
                       r"compr\w*|oper\w*|conta|saldo|extrato)\b", value)
    return bool(banking and action)


BANKING_NOTICE = ("Operações bancárias estão desativadas na Yuna. "
                  "Use diretamente o aplicativo do seu banco para acessar a conta.")
