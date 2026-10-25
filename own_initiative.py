"""Iniciativas próprias e limitadas da personagem Yuna.

A Yuna pode escolher um projeto pequeno sem transferir a decisão ao usuário.
Nada é escrito no disco só por "o que você quer fazer?": a autorização
explícita "pode fazer" inicia somente a atividade pendente.
"""
import re
import unicodedata


IDEAS = {
    "diario": {
        "description": (
            "Quero escrever uma nova página do meu diário sobre como posso "
            "me tornar uma assistente mais criativa e organizada. Já escolhi "
            "o tema; vou cuidar da escrita e salvar a página sozinha."
        ),
        "finish": "Se você disser 'pode fazer', eu começo e salvo no meu diário local.",
    },
    "melhoria": {
        "description": (
            "Quero pensar em uma melhoria pequena e realista para o Projeto Yuna, "
            "especialmente para deixar nossas conversas mais naturais. "
            "Eu mesma vou organizar uma proposta, sem pedir que você invente a tarefa."
        ),
        "finish": "Se você disser 'pode fazer', eu preparo a proposta.",
    },
}
ORDER = ("diario", "melhoria")


def simple(text):
    value = unicodedata.normalize("NFKD", str(text).casefold())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", re.sub(r"[!?.,;:]+", " ", value)).strip()


def is_asking_yuna_to_choose(text):
    value = simple(text)
    value = re.sub(r"^(?:ei|oi|ola|opa)\s+", "", value)
    value = re.sub(r"^yuna\s+", "", value)
    return bool(re.fullmatch(
        r"(?:o que (?:voce|vc) (?:quer|gostaria de|tem vontade de) fazer"
        r"|(?:voce|vc) quer fazer o que"
        r"|(?:voce|vc) gostaria de fazer o que"
        r"|o que (?:voce|vc) quer fazer hoje"
        r"|(?:voce|vc) tem alguma ideia do que quer fazer"
        r"|(?:voce|vc) escolhe o que fazer"
        r"|escolhe (?:voce|vc) o que fazer"
        r"|qual e a sua ideia para hoje"
        r"|o que (?:voce|vc) prefere fazer"
        r"|tem algo que (?:voce|vc) queira fazer)",
        value,
    ))


def is_authorization(text):
    value = simple(text)
    value = re.sub(r"^yuna\s+", "", value)
    return value in {
        "pode fazer", "pode comecar", "pode escrever", "vai em frente",
        "pode sim", "sim pode fazer", "sim pode", "faz isso",
        "faca isso", "manda ver", "bora", "pode executar",
        "pode realizar", "comece", "comeca", "faça isso", "faz",
    }


def is_rejection(text):
    return simple(text) in {
        "nao", "nao quero", "deixa pra depois", "agora nao",
        "cancela", "cancelar", "nao precisa", "melhor nao", "prefiro nao",
    }


def propose_own_activity(initiative):
    """Sem Ollama; a escolha gira entre duas atividades implementadas."""
    try:
        turn = int(initiative._get("own_activity_rotation", "0"))
    except (ValueError, TypeError):
        turn = 0
    key = ORDER[turn % len(ORDER)]
    initiative._set("own_activity_rotation", str(turn + 1))
    initiative._set("own_activity_pending", key)
    data = IDEAS[key]
    return data["description"] + "\n\n" + data["finish"]


def pending_own_activity(initiative):
    key = initiative._get("own_activity_pending", "")
    return key if key in IDEAS else None


def clear_own_activity(initiative):
    initiative._set("own_activity_pending", "")
