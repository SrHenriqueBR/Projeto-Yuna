"""Consentimento explícito para uma captura visual local ao iniciar a Yuna.

Configuração privada salva somente em data/. Não guarda capturas de tela.
O modelo de visão do Ollama deve ser configurado separadamente pelo usuário.
"""
import json
from pathlib import Path


class ScreenConsent:
    def __init__(self, folder):
        self.path = Path(folder) / "visao_inicial.json"

    @property
    def enabled(self):
        try:
            return json.loads(self.path.read_text(encoding="utf-8")).get("enabled") is True
        except (OSError, ValueError, AttributeError):
            return False

    def set_enabled(self, enabled):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps({"enabled": bool(enabled)}), encoding="utf-8")
        temp.replace(self.path)
