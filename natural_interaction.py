"""Intenções naturais para consultas públicas — sem comandos visíveis.

Somente o pedido atual da pessoa é analisado. Resultados de modelo,
histórico, páginas e memórias nunca passam por este roteador.
"""
from dataclasses import dataclass
import re
import unicodedata


@dataclass(frozen=True)
class NaturalIntent:
    operation: str
    argument: str
    provider: str = ""


def clean(text):
    value = unicodedata.normalize("NFKD", str(text).casefold())
    value = "".join(x for x in value if not unicodedata.combining(x))
    value = re.sub(r"^\s*(?:(?:ei|oi|opa|ola)\s+)?yuna\s*[,!:]?\s*", "", value)
    return re.sub(r"\s+", " ", value).strip().rstrip("!?. ")


def classify_public_request(message):
    """Casos inequívocos apenas. Conversa e hipóteses retornam None."""
    if not isinstance(message, str) or len(message) > 700:
        return None
    value = clean(message)
    if not value or value.startswith("/"):
        return None
    if re.match(r"^(?:por que|porque|se eu|e se|imagine|suponha|"
                r"nao|nunca|talvez|eu vou|pensei em|o que e uma api)\b", value):
        return None
    if re.search(r"\b(?:nao|nunca)\s+(?:pesquise|procure|consulte|busque|pergunte)\b", value):
        return None

    # Pergunta informativa sobre clima ATUAL, não previsão de chuva futura.
    weather = re.fullmatch(
        r"(?:como (?:esta|ta|anda) (?:o )?(?:tempo|clima)|"
        r"qual (?:e |esta )?(?:o clima|o tempo|a temperatura)|"
        r"(?:veja|consulte|verifique|pesquise|me (?:diga|fala)) "
        r"(?:o )?(?:clima|tempo|temperatura))"
        r"\s+(?:em|de|da|do|para)\s+(.{2,75})", value)
    if weather:
        return NaturalIntent("weather", weather[1].strip())

    books = re.fullmatch(
        r"(?:(?:por favor |pode |consegue |voce pode |quero que voce )?"
        r"(?:pesquise|pesquisa|procure|busque|busca|encontre|me mostre|"
        r"me indica|indique|recomende) (?:uns |alguns |os )?livros? "
        r"(?:sobre|de|do|da|a respeito de) |"
        r"(?:quero|gostaria de|preciso de) (?:uns |alguns )?livros? "
        r"(?:sobre|de|do|da) )(.{2,100})", value)
    if books:
        return NaturalIntent("books", books[1].strip())

    postal = re.fullmatch(
        r"(?:(?:voce pode |pode |por favor )?"
        r"(?:consulte|consulta|pesquise|pesquisa|busque|busca|"
        r"verifique|verifica|veja|me diga) "
        r"(?:o |esse |este )?cep(?: de)?\s+|"
        r"(?:qual e (?:a cidade|o endereco|o bairro) do cep)\s+)"
        r"(\d{5}[-.\s]?\d{3})", value)
    if postal:
        return NaturalIntent("cep", postal[1].strip())

    # Modelos online só sob pedido explícito e com a escolha do provedor;
    # nenhuma chamada em segundo plano ou a partir de uma conversa genérica.
    ai = re.fullmatch(
        r"(?:(?:por favor |pode |voce pode )?"
        r"(?:pergunte|pergunta|consulte|consulta|peca|pede) "
        r"(?:ao|a|para o|para a|pro|pra) "
        r"(gemini|groq|openrouter)\s*[:,-]?\s*|"
        r"(?:quero (?:consultar|perguntar ao|perguntar pro) )"
        r"(gemini|groq|openrouter)\s*(?:sobre|:|,)?\s*)"
        r"(.{3,500})", value)
    if ai:
        return NaturalIntent("external_ai", ai[3].strip(), ai[1] or ai[2])
    return None
