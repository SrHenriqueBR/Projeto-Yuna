"""Seleção de voz conforme preferência explícita, não gênero presumido.

O catálogo de vozes instaladas depende do Windows; falhas são informadas.
"""


def preferred_voice_gender(presentation):
    options = {"feminina": "Female", "masculina": "Male", "neutra": None}
    if presentation not in options:
        raise ValueError("Apresentação de voz desconhecida")
    return options[presentation]


def select_installed_voice(voices, presentation="feminina"):
    """Escolhe uma voz pt-BR habilitada, ou retorna None se indisponível.

    voices: iterável de dicionários name/culture/gender/enabled.
    Não troca para gênero diferente silenciosamente.
    """
    gender = preferred_voice_gender(presentation)
    candidates = [
        voice for voice in voices
        if voice.get("enabled", True)
        and str(voice.get("culture", "")).lower() == "pt-br"
        and voice.get("name")
    ]
    if gender is not None:
        candidates = [v for v in candidates if v.get("gender") == gender]
    return candidates[0]["name"] if candidates else None
