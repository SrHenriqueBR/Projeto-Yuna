"""Preferências locais por usuário, sem inferir identidade a partir da voz.

A autoria do projeto é fixa; usuários podem mudar apresentação e voz.
"""
from dataclasses import dataclass, replace

CREATOR = "Kaizen"
PRESENTATIONS = frozenset({"feminina", "masculina", "neutra"})
VOICE_STYLES = frozenset({"suave", "natural", "energica"})


@dataclass(frozen=True)
class PersonaPreferences:
    presentation: str = "feminina"
    voice_style: str = "natural"
    display_name: str = "Yuna"

    def updated(self, *, presentation=None, voice_style=None, display_name=None):
        if presentation is not None and presentation not in PRESENTATIONS:
            raise ValueError("Apresentação indisponível")
        if voice_style is not None and voice_style not in VOICE_STYLES:
            raise ValueError("Estilo de voz indisponível")
        if display_name is not None and (
                not isinstance(display_name, str)
                or not 1 <= len(display_name.strip()) <= 32):
            raise ValueError("Nome de exibição inválido")
        return replace(
            self,
            presentation=self.presentation if presentation is None else presentation,
            voice_style=self.voice_style if voice_style is None else voice_style,
            display_name=self.display_name if display_name is None else display_name.strip(),
        )


def creator_statement():
    return f"Meu projeto foi criado por {CREATOR}. Isso não autentica quem está falando comigo."
