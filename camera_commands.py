"""Reconhece pedidos diretos para ABRIR o seletor, nunca para ligar câmera sozinho."""
import re
import unicodedata


def is_camera_view_request(text):
    if not isinstance(text, str) or len(text) > 180:
        return False
    folded = unicodedata.normalize("NFKD", text)
    folded = "".join(char for char in folded if not unicodedata.combining(char))
    folded = re.sub(r"[^a-z0-9 ]+", " ", folded.casefold())
    folded = re.sub(r"\s+", " ", folded).strip()
    return bool(re.fullmatch(
        r"(?:yuna )?"
        r"(?:(?:voce )?(?:pode |consegue ))?"
        r"(?:abra|abre|abrir|mostra|mostre|mostrar|veja|visualize|quero ver|quero abrir)"
        r" (?:a |as |minha |minhas |uma )?"
        r"(?:camera|cameras|webcam|webcams|cftv)"
        r"(?: (?:da|do|de) [a-z0-9 ]{1,50})?",
        folded,
    ))
