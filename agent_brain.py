"""Yuna: planejamento local de tarefas permitidas."""

from dataclasses import dataclass
from pathlib import Path
import re
import zipfile

from document_writer import FileRequest, known_folder, validate_title
from office_agent import folded, create_requested
from web_actions import wikipedia_lookup

@dataclass(frozen=True)
class TaskPlan:
    topic: str
    output: FileRequest

FORMATS = {
    "powerpoint": ("powerpoint", "pptx", "apresentacao", "slides"),
    "excel": ("excel", "xlsx", "planilha"),
    "pdf": ("pdf",),
    "word": ("word", "docx", "documento"),
    "markdown": ("markdown", "md"),
    "texto": ("txt", "texto", "arquivo"),
}
SUFFIX = {"powerpoint": ".pptx", "excel": ".xlsx", "pdf": ".pdf",
          "word": ".docx", "markdown": ".md", "texto": ".txt"}
SEARCH = r"(?:pesquise|pesquisa|pesquisar|busque|buscar|procure|investigue)"
MAKE = r"(?:crie|cria|criar|faca|faz|fazer|monte|montar|gere|gerar|produza)"
PRIVATE = re.compile(r"\b(?:meu|minha|meus|minhas|senha|cpf|token|"
                     r"cartao|conta|extrato|endereco|memoria|conversa|pix)\b|@|[/\\]", re.I)

def plan_request(message, home=None):
    """Deterministic routing; returns None for ordinary chat and single tasks."""
    if not isinstance(message, str) or not message.strip():
        return None
    if len(message) > 600:
        raise ValueError("Pedido muito longo: máximo de 600 caracteres.")
    value = folded(message.strip())
    value = re.sub(r"^(?:yuna|ei yuna)[, :]+", "", value)
    if re.match(r"^(?:como|por que|porque|e se|se eu|nao|nunca)\b", value):
        return None
    search = re.search(r"\b" + SEARCH + r"\b\s*(?:sobre\s+|a respeito de\s+)?", value)
    if search is None:
        return None
    tail = value[search.end():]
    join = re.search(r"(?:,|\s+e\s+|\s+depois\s+)\s*(?:depois\s+)?"
                     + MAKE + r"\b", tail)
    if join is None:
        return None
    topic = tail[:join.start()].strip(" ,.;!?")
    if not 3 <= len(topic) <= 100 or PRIVATE.search(topic):
        raise ValueError("Use um tema público de 3 a 100 caracteres, sem dados pessoais.")
    remainder = tail[join.end():]
    kind = next((name for name, words in FORMATS.items()
                 if any(re.search(r"\b" + re.escape(word) + r"\b", remainder)
                        for word in words)), None)
    if kind is None:
        raise ValueError("Informe Word, Excel, PowerPoint, PDF, TXT ou Markdown.")
    folders = r"(documentos|documents|downloads|area de trabalho|desktop)"
    dest = re.search(r"\b(?:na|no|nos|nas|em)\s+(?:minha|meu|pasta)?\s*"
                     + folders + r"\b", remainder)
    folder = dest[1] if dest else "Documentos"
    if dest is None and re.search(r"\b(?:pasta|caminho|diretorio)\s+[^ ]", remainder):
        raise ValueError("Escolha outra pasta usando o seletor de arquivos.")
    quoted = re.search(r'["“]([^"”]{1,95})["”]', message)
    name = quoted[1] if quoted else ("Pesquisa - " + topic.title())[:90]
    return TaskPlan(topic, FileRequest(
        kind, validate_title(name), known_folder(folder, home),
        "Síntese da pesquisa pública sobre " + topic + ", com referências verificáveis."
    ))
