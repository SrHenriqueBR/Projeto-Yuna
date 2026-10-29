"""Comandos explícitos em português para preferências da voz da Yuna.

Não trata menções casuais de gênero, filmes ou outras pessoas como comandos.
"""
import re
import unicodedata


def _normal(text):
    if not isinstance(text, str):
        return ""
    folded = unicodedata.normalize("NFKD", text)
    folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", folded.lower())).strip()


def parse_voice_preference(text):
    """Retorna campos a atualizar ou None (sem pedido explícito)."""
    normalized = re.sub(r"^yuna\s+", "", _normal(text))
    if not re.match(
        r"^(?:quero (?:que |uma? |sua |a sua |voce |voz )|"
        r"muda(?:r)? |mude |troca(?:r)? |troque |"
        r"fale |fala |use |usa |vire |vira |seja |"
        r"deixa(?:r)? |deixe |coloca(?:r)? |coloque |"
        r"prefiro |escolha |escolhe |volta(?:r)? |volte )", normalized
    ):
        return None
    result = {}
    if re.search(r"\b(masculin[oa]?|homem|rapaz|garoto)\b", normalized):
        result["presentation"] = "masculina"
    elif re.search(r"\b(feminin[oa]?|mulher|mo[cç]a|garota)\b", normalized):
        result["presentation"] = "feminina"
    elif re.search(r"\b(neutr[oa]|sem genero|sem preferencia de genero)\b", normalized):
        result["presentation"] = "neutra"

    if re.search(r"\b(suave|calma|delicada|macia)\b", normalized):
        result["voice_style"] = "suave"
    elif re.search(r"\b(energica|animada|agitada|empolgada)\b", normalized):
        result["voice_style"] = "energica"
    elif re.search(r"\b(natural|normal|original)\b", normalized):
        result["voice_style"] = "natural"

    return result or None
