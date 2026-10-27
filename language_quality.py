"""Qualidade de português e continuidade da identidade da Yuna.

Respostas determinísticas limitadas a perguntas de identidade e saudações.
Não tenta reescrever textos livres, documentos, citações ou código.
"""
import re
import unicodedata


def normalized(text):
    value = unicodedata.normalize("NFKD", str(text).casefold())
    value = "".join(x for x in value if not unicodedata.combining(x))
    value = re.sub(r"[!?.,;:]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return re.sub(r"^(?:ei |oi |ola )?yuna\s+", "", value)


def identity_conversation_reply(text, history=None):
    """Pequenos turnos onde a identificação não depende de texto inventado por LLM."""
    value = normalized(text)
    if value in (
        "ola yuna tudo bem", "ola tudo bem", "oi yuna tudo bem",
        "oi tudo bem", "tudo bem yuna", "yuna tudo bem",
        "ola yuna tudo bom", "oi yuna tudo bom", "tudo bom yuna",
        "tudo bom", "tudo bem",
    ):
        return "Oi, Kaizen! Tudo bem por aqui. E com você? 🖤"
    if value in ("voce e a yuna", "voce e yuna", "voce e minha criacao",
                 "voce e a minha criacao"):
        return "Sou a Yuna, sim! Você criou o Projeto Yuna, Kaizen. 🖤"
    if value in ("qual e o seu nome", "e o seu nome", "qual seu nome",
                 "e o seu", "isso e o seu", "isso e o seu nome"):
        # "E o seu?" é ambíguo: só responder identidade se o assunto anterior
        # foi o nome da pessoa.
        if value in ("e o seu", "isso e o seu"):
            turns = (history or [])[-4:]
            prior = " ".join(row.get("content", "") for row in turns)
            if not re.search(r"\b(?:nome|me chamo|chama)\b", normalized(prior)):
                return None
        return "Meu nome é Yuna, Kaizen. Sou sua assistente pessoal. ✨"
    if "minha criacao" in value and (
            re.search(r"\b(?:voce e|tu es|te criei|eu criei|criei voce)\b", value)):
        return "Isso mesmo, Kaizen. Você criou a Yuna! Obrigada por cuidar do projeto. 🖤"
    return None


# Padrões conhecidos de linguagem artificial e troca de papéis.
# Nenhuma troca automática de flexão em palavras citadas ou em conteúdos de terceiros.
BAD_PATTERNS = (
    r"\b(?:eu\s+)?vou\s+(?:pode|precisa|quer|vai|sou|gostaria)\b",
    r"\b(?:eu\s+)?sou\s+(?:chama|chamado|chamado de)\b",
    r"\b(?:eu\s+)?sou\s+muito\s+especial\s+ter\b",
    r"\b(?:eu\s+)?vou\s+(?:poder|precisar)\s+de\s+abrir\b",
    r"\bseu\s+nome\s+(?:e|é)\s+yuna\b",
    r"\b(?:eu )?sou (?:o )?kaizen\b",
    r"\b(?:nao|não)\s+tenho\s+(?:um\s+)?nome\s+pr[oó]prio\b",
    r"\b(?:eu )?(?:estou|fiquei|sou|me sinto)\s+(?:muito\s+)?"
    r"(?:pronto|animado|grato|cansado|confuso|empolgado)\b",
    r"(?m)^\s*obrigado(?:[,!. ]|$)",
)


def has_language_problem(answer):
    if not isinstance(answer, str) or not answer.strip():
        return True
    # Evitar avaliar código, citações e blocos que não são da própria Yuna.
    prose = re.sub(r"(?s)\x60{3}.*?\x60{3}|\x60[^\x60]*\x60", "", answer)
    prose = re.sub(r"(?m)^\s*>.*$", "", prose)
    prose = re.sub(r'“[^”\n]*”|"[^"\n]*"', "", prose)
    return any(re.search(pattern, prose, re.I) for pattern in BAD_PATTERNS)
