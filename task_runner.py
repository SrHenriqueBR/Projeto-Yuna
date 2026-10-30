"""Sequências pequenas pedidas pela pessoa; nenhuma ação nasce de texto do modelo."""
from dataclasses import dataclass
import re

from computer import command_text, open_steam
from development_lab import check_cancel
from web_actions import wikipedia_lookup, open_allowed_url, public_search_query
from urllib.parse import urlencode


@dataclass(frozen=True)
class Step:
    action: str
    argument: str = ""


FOLDERS = {"downloads": "downloads", "documentos": "documentos",
           "area de trabalho": "desktop", "explorador": "explorador",
           "explorador de arquivos": "explorador", "desktop": "desktop"}
INTERPRETERS = re.compile(
    r"\b(?:cmd|powershell|pwsh|terminal|python\d*|wscript|cscript|bash|sh|regedit|rundll32|mshta)\b"
)
TASK_PREFIX = "/tarefas"


def _parse_step(text):
    value = command_text(text)
    if re.search(r"\b(?:nao|nunca)\b", value) or any(c in value for c in "\r\n\x00`\"<>|&"):
        raise ValueError("A sequência contém negação, texto citado ou uma etapa ambígua.")
    match = re.fullmatch(r"(?:abra|abre|abrir|inicie|iniciar) (?:o |a )?(?:pasta |aplicativo |programa )?(.{1,80})", value)
    if match:
        name = match[1].strip()
        if name in FOLDERS:
            return Step("folder", FOLDERS[name])
        if not re.fullmatch(r"[\w .+()\-]{1,80}", name) or INTERPRETERS.search(name):
            raise ValueError("Use somente o nome de um aplicativo comum nessa sequência.")
        return Step("app", name)
    if value in ("/sistema", "mostre o sistema", "mostre as informacoes do computador", "verifique o sistema"):
        return Step("system")
    if value in ("/processos", "mostre os processos", "liste os processos"):
        return Step("processes")
    if value in ("/apps", "liste os aplicativos", "mostre os aplicativos"):
        return Step("apps")
    match = re.fullmatch(r"(?:/buscar|busque|procure) (?:o arquivo |a pasta |arquivos? |pastas? )(.{1,100})", value)
    if match:
        return Step("files", match[1])
    match = re.fullmatch(r"(?:pesquise|pesquisa|busque) (?:na web|na internet) (?:sobre )?(.{3,160})", value)
    if match:
        return Step("web", public_search_query(match[1]))
    match = re.fullmatch(r"(?:pesquise|pesquisa) (?:sobre )?(.{3,160})", value)
    if match:
        return Step("research", public_search_query(match[1]))
    raise ValueError("Não tenho uma etapa definida para: " + text[:100]
                     + ". Use abrir app/pasta, buscar arquivo, pesquisar, sistema ou processos.")


def plan_tasks(message):
    """Só conectores explícitos; validar tudo antes da primeira ação."""
    if not isinstance(message, str) or len(message) > 1200:
        return None
    value = command_text(message)
    explicit = value.startswith(TASK_PREFIX + " ")
    if explicit:
        value = value[len(TASK_PREFIX):].strip()
    elif not re.match(r"^(?:abra|abre|inicie|pesquise|pesquisa|busque|procure|mostre|liste|verifique)\b", value):
        return None
    # Sem "e depois", não dividir nomes/assuntos como "pesquise café e chá".
    pieces = re.split(r"\s*;\s*|\s*,?\s+e depois\s+|\s*,?\s+depois\s+|\s*,?\s+em seguida\s+", value)
    if len(pieces) == 1 and not explicit:
        return None
    if not 1 <= len(pieces) <= 5 or any(not part.strip() for part in pieces):
        raise ValueError("Peça de 1 a 5 etapas completas, separadas por 'e depois'.")
    return tuple(_parse_step(piece) for piece in pieces)


def execute_tasks(steps, computer, open_folder, *, progress=None, cancelled=None):
    """Sequencial para respeitar dependências, sem cliques ou comandos arbitrários."""
    if not isinstance(steps, tuple) or not 1 <= len(steps) <= 5 or any(not isinstance(s, Step) for s in steps):
        raise ValueError("Plano de tarefas inválido.")
    progress = progress or (lambda text: None)
    results = []
    for number, step in enumerate(steps, 1):
        try:
            check_cancel(cancelled)
            progress(f"Etapa {number}/{len(steps)} · {step.action}: {step.argument}".rstrip())
            if step.action == "folder":
                answer = open_folder(step.argument)
            elif step.action == "app":
                answer = open_steam() if step.argument == "steam" else computer.desktop.open_app(step.argument)
            elif step.action == "system":
                answer = computer.desktop.system_info()
            elif step.action == "processes":
                answer = computer.desktop.processes()
            elif step.action == "apps":
                answer = computer.desktop.list_apps()
            elif step.action == "files":
                answer = computer.search(step.argument, False)
            elif step.action == "research":
                answer = wikipedia_lookup(step.argument)
            elif step.action == "web":
                answer = open_allowed_url("https://www.google.com/search?" + urlencode({"q": step.argument}))
            else:
                raise ValueError("Etapa não implementada.")
            results.append(f"{number}. {answer}")
            # As ferramentas antigas retornam texto. Uma dúvida/lista de apps ou
            # falha conhecida interrompe a sequência, em vez de afirmar sucesso.
            if re.search(r"(?i)^(?:não |estas ações|a abertura .*windows|essa pesquisa|nenhum resultado)", answer) or (
                    step.action == "app" and "Lista de até" in answer):
                results.append("Sequência interrompida nesta etapa. Confira o resultado antes de continuar.")
                break
            check_cancel(cancelled)
        except InterruptedError:
            results.append("Sequência cancelada. Ações já solicitadas não são desfeitas.")
            break
        except (RuntimeError, OSError, ValueError) as exc:
            results.append(f"{number}. Não concluí esta etapa: {exc}")
            results.append("As etapas seguintes não foram executadas.")
            break
    return "Sequência de tarefas:\n\n" + "\n\n".join(results)


HELP = ("Peça uma sequência de até 5 etapas. Exemplo:\n"
        "Yuna, abra Downloads e depois abra Steam\n"
        "/tarefas mostre os processos; pesquise sobre astronomia\n"
        "Mostro cada resultado. Abrir um aplicativo é uma solicitação ao Windows; "
        "confira sua janela. Parar interrompe antes da próxima etapa, sem desfazer as anteriores.")
