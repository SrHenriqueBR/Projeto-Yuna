"""Diagnóstico local verificável de criação de arquivos, sem usar Ollama.

Não executa programas nem remove/substitui arquivos. Um arquivo TXT de teste
só é escrito quando a pessoa pede explicitamente /teste_arquivo.
"""
import importlib.util
import sys
from datetime import datetime
from pathlib import Path

from document_writer import known_folder, _reserve_unique_file


def runtime_report(version, project_root):
    root = Path(project_root).resolve()
    agent_file = importlib.util.find_spec("office_agent")
    writer_file = importlib.util.find_spec("document_writer")
    libraries = {
        "python-docx": "docx",
        "openpyxl": "openpyxl",
        "python-pptx": "pptx",
        "reportlab": "reportlab",
    }
    present = {
        display: "instalado" if importlib.util.find_spec(module) is not None
                 else "NÃO instalado"
        for display, module in libraries.items()
    }
    return (
        f"Yuna versão {version}\n"
        f"Pasta da Yuna em execução: {root}\n"
        f"Python em execução: {sys.executable}\n"
        f"Roteador de arquivos: {agent_file.origin if agent_file else 'AUSENTE'}\n"
        f"Gerador de documentos: {writer_file.origin if writer_file else 'AUSENTE'}\n"
        + "\n".join(f"{name}: {state}" for name, state in present.items())
        + "\nPara comprovar a gravação na sua Área de Trabalho, digite /teste_arquivo."
    )


def create_test_file():
    """A escrita só acontece por pedido explícito /teste_arquivo."""
    directory = known_folder("Área de Trabalho")
    target = _reserve_unique_file(directory, "Yuna_Teste_Arquivo", ".txt")
    try:
        target.write_text(
            "Teste de criação da Yuna realizado pelo código Python local.\n"
            f"Data e horário do Windows: {datetime.now().astimezone():%d/%m/%Y %H:%M}\n"
            "Este TXT verifica somente a permissão de gravar arquivos. "
            "A criação de Word ainda depende de python-docx e Ollama.\n",
            encoding="utf-8"
        )
        if not target.is_file() or target.stat().st_size <= 0:
            raise OSError("O arquivo de teste não foi gravado corretamente.")
        return (
            "✅ Teste concluído: arquivo TXT criado de verdade.\n"
            f"Caminho completo: {target}\n"
            "Confira no Explorador. Agora teste: "
            "'Crie um Word chamado Diário da Yuna na Área de Trabalho'."
        )
    except Exception:
        target.unlink(missing_ok=True)
        raise
