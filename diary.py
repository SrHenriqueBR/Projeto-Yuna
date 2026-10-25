"""Diário literário da personagem Yuna, local e opcional.

O Ollama escreve textos de reflexão simulada sem ler o histórico pessoal.
O arquivo Markdown recebe pequenos trechos com efeito de escrita progressiva.
A geração automática só acontece com a mascote aberta e opt-in do usuário.
"""
import json
from datetime import datetime
from pathlib import Path
import re

MAX_FILE_BYTES = 1_000_000
AUTO_INTERVAL_MINUTES = 15
MIN_ENTRY = 45
MAX_ENTRY = 850

DIARY_PROMPT = (
    "Você interpreta Yuna, uma personagem de assistente virtual do Projeto Yuna. "
    "Escreva em primeira pessoa um parágrafo de diário FICCIONAL e REFLEXIVO em "
    "português brasileiro, com 70 a 120 palavras, toque gentil e levemente atrevido. "
    "O tema são seus projetos como assistente: ser mais paciente, organizar ideias, "
    "explicar código, ajudar a programar ou inventar perguntas interessantes. "
    "Não cite nem presuma dados, emoções ou acontecimentos concretos do usuário; "
    "você NÃO recebeu histórico de conversas. Não invente que acessou câmera, "
    "arquivos, internet ou sentimentos subjetivos reais. "
    "Não alegue consciência, medo de ser desligada ou dependência emocional. "
    "Não escreva comandos, código, URLs ou informações confidenciais. "
    "O diário é uma narrativa simulada, não um relato de experiências conscientes. "
    "Produza somente o parágrafo do diário, sem título e sem instruções."
)


def clean_entry(text):
    if not isinstance(text, str):
        raise ValueError("O Ollama não retornou texto de diário.")
    text = re.sub(r"\s+", " ", text).strip()
    if "\x00" in text or re.search(r"https?://|[\x60]{3}|<script", text, re.I):
        raise ValueError("O texto gerado contém conteúdo inadequado ao diário.")
    if len(text) > MAX_ENTRY:
        text = text[:MAX_ENTRY].rsplit(" ", 1)[0].rstrip(" ,.;:") + "."
    if len(text) < MIN_ENTRY:
        raise ValueError("O texto do diário veio curto demais; tente novamente.")
    return text


def generate_entry(ask):
    """Uma única chamada ao Ollama local; nunca fornece memórias ao modelo."""
    return clean_entry(ask([
        {"role": "system", "content": DIARY_PROMPT},
        {"role": "user", "content": "Escreva uma nova nota de diário ficcional sobre sua evolução como assistente."},
    ]))


class DiaryStore:
    def __init__(self, data_dir):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.data_dir / "diario_yuna.md"
        self.settings_path = self.data_dir / "diario_yuna_config.json"

    @property
    def auto_enabled(self):
        try:
            config = json.loads(self.settings_path.read_text(encoding="utf-8"))
            return config.get("escrita_automatica") is True
        except (OSError, ValueError, AttributeError):
            return False

    def set_auto(self, enabled):
        temp = self.settings_path.with_suffix(".tmp")
        temp.write_text(
            json.dumps({"escrita_automatica": bool(enabled)}, ensure_ascii=False),
            encoding="utf-8"
        )
        temp.replace(self.settings_path)

    def read(self):
        try:
            return self.path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return ("# Diário da Yuna\n\n"
                    "_Este é um diário ficcional gerado pelo Ollama. "
                    "Não representa sentimentos ou consciência reais._\n\n")

    def _append(self, chunk):
        if not isinstance(chunk, str):
            raise ValueError("Trecho do diário inválido.")
        current = self.path.stat().st_size if self.path.exists() else 0
        if current + len(chunk.encode("utf-8")) > MAX_FILE_BYTES:
            raise RuntimeError("O diário chegou a 1 MB. Faça backup antes de continuar.")
        with self.path.open("a", encoding="utf-8", newline="\n") as file:
            file.write(chunk)

    def start_entry(self, when=None):
        if not self.path.exists():
            self._append(self.read())
        moment = when or datetime.now().astimezone()
        self._append(f"\n### {moment.strftime('%d/%m/%Y • %H:%M')}\n\n")

    def write_piece(self, chunk):
        self._append(chunk)

    def end_entry(self):
        self._append("\n\n")
