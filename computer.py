"""Busca local por nomes e abertura de resultados escolhidos pelo usuário."""
from collections import deque
import ctypes
import os
from pathlib import Path
import re
import stat
import time
import unicodedata


def normalize(text):
    text = unicodedata.normalize('NFKD', text.casefold())
    return ''.join(c for c in text if not unicodedata.combining(c))



def command_text(text):
    value = re.sub(r'\s+', ' ', normalize(text)).strip().rstrip('.!?')
    value = re.sub(r'^yuna[, ]+', '', value)
    value = re.sub(r'^por favor[, ]+', '', value)
    value = re.sub(r'[, ]+por favor$', '', value)
    value = re.sub(r'^(?:voce )?(?:pode|consegue) ', '', value)
    # Variações coloquiais somente após o verbo, sem remover negações.
    value = re.sub(r'^(abra|abre|abrir|inicie|iniciar|execute|executar) (?:pra|para) (?:mim|min) ',
                   r'\1 ', value)
    return value


def open_steam():
    if os.name != 'nt':
        return 'A abertura da Steam está disponível somente no Windows.'
    try:
        # Destino fixo; nenhum argumento do usuário vira comando ou URL.
        os.startfile('steam://open/main', 'open')
    except OSError as exc:
        return ('Não consegui solicitar a abertura da Steam. Verifique se o aplicativo está instalado '
                f'e se abre pelo menu Iniciar. Detalhe: {exc}')
    return 'Solicitei ao Windows a abertura da Steam. Confira a janela do aplicativo.'


def fixed_drives():
    if os.name != 'nt':
        return [Path.home()]
    get_type = ctypes.windll.kernel32.GetDriveTypeW
    get_type.argtypes = [ctypes.c_wchar_p]
    get_type.restype = ctypes.c_uint
    return [Path(f'{letter}:\\') for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
            if get_type(f'{letter}:\\') == 3]


# Ignora diretórios de sistema, caches e dependências. Não contorna permissões.
SKIP = {'windows', 'program files', 'program files (x86)', 'programdata',
        'appdata', '$recycle.bin', 'system volume information',
        'node_modules', '.git', '.venv', 'venv', '__pycache__', '.cache'}
# Arquivos desconhecidos podem ser localizados no Explorer, mas não executados.
DOCUMENTS = {'.txt', '.pdf', '.docx', '.xlsx', '.pptx', '.odt', '.ods',
             '.csv', '.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif',
             '.mp3', '.wav', '.mp4', '.mkv'}


def is_link(path):
    info = path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def search_names(query, roots, max_results=50, max_entries=100000, seconds=20):
    """Bounded breadth-first traversal. File contents are never opened."""
    terms = normalize(query).split()
    if not terms or len(query) > 200:
        raise ValueError('Informe um nome ou parte dele, com até 200 caracteres.')
    queue = deque(Path(r).absolute() for r in roots)
    seen, results = set(), []
    scanned = skipped = 0
    deadline = time.monotonic() + seconds
    reason = None
    try:
        while queue:
            if time.monotonic() >= deadline:
                reason = 'limite de tempo'
                break
            folder = queue.popleft()
            key = os.path.normcase(str(folder))
            if key in seen:
                continue
            seen.add(key)
            try:
                if is_link(folder):
                    skipped += 1
                    continue
                with os.scandir(folder) as entries:
                    for entry in entries:
                        if scanned >= max_entries or time.monotonic() >= deadline:
                            reason = 'limite de itens ou tempo'
                            break
                        scanned += 1
                        path = Path(entry.path)
                        try:
                            if is_link(path):
                                skipped += 1
                                continue
                            directory = entry.is_dir(follow_symlinks=False)
                            if directory and entry.name.casefold() in SKIP:
                                skipped += 1
                                continue
                            if all(term in normalize(entry.name) for term in terms):
                                results.append(path)
                                if len(results) >= max_results:
                                    reason = 'limite de resultados'
                                    break
                            if directory:
                                queue.append(path)
                        except OSError:
                            skipped += 1
                if reason:
                    break
            except OSError:
                skipped += 1
    except KeyboardInterrupt:
        reason = 'cancelada pelo usuário'
    return results, {'scanned': scanned, 'skipped': skipped, 'reason': reason}


class Computer:
    def __init__(self):
        from desktop import Desktop
        self.desktop = Desktop()
        self.results = []

    def search(self, query, everywhere=False):
        self.results = []
        roots = fixed_drives() if everywhere else [Path.home()]
        # Perfil primeiro para que a busca ampla priorize os documentos pessoais.
        if everywhere:
            roots = [Path.home()] + roots
        print('Buscando nomes de arquivos e pastas… Ctrl+C interrompe a busca.')
        self.results, stats = search_names(query, roots)
        lines = [f'Escopo: {", ".join(str(r) for r in roots)}']
        for number, path in enumerate(self.results, 1):
            lines.append(f'{number}. {path}')
        if not self.results:
            lines.append('Nenhum resultado encontrado na parte pesquisada.')
        lines.append(f'Itens examinados: {stats["scanned"]}; itens/pastas ignorados: {stats["skipped"]}.')
        if stats['reason']:
            lines.append(f'Busca parcial: {stats["reason"]}. Refine o nome procurado.')
        else:
            lines.append('Busca concluída no escopo acessível, com as exclusões indicadas em /ajuda.')
        if self.results:
            lines.append('Use /abrir 1 para abrir o item ou /localizar 1 para abrir a pasta que o contém.')
        return '\n'.join(lines)

    def open_result(self, number, locate=False):
        if number < 1 or number > len(self.results):
            return 'Resultado inválido. Faça uma busca e escolha um número da lista atual.'
        path = self.results[number - 1]
        if os.name != 'nt':
            return 'A abertura de resultados está disponível somente no Windows.'
        try:
            if not path.exists():
                return 'Esse item não existe mais. Faça a busca novamente.'
            if is_link(path):
                return 'O item mudou para um link. Faça uma nova busca.'
            directory = path.is_dir()
            if not locate and not directory and path.suffix.lower() not in DOCUMENTS:
                return 'Esse tipo de arquivo não é aberto automaticamente. Use /localizar para ver a pasta.'
            target = path.parent if locate else path
            os.startfile(str(target), 'open')
            return f'Solicitei ao Windows a abertura de: {target}'
        except OSError as exc:
            return f'Não foi possível abrir o item: {exc}'

    def handle(self, text):
        """Return None for ordinary conversation; never run text supplied by the model."""
        value = command_text(text)
        if value == '/apps atualizar':
            self.desktop.refresh()
            return self.desktop.list_apps()
        if value == '/apps' or value.startswith('/apps '):
            return self.desktop.list_apps(value[5:].strip())
        if value in ('/sistema', 'mostre as informacoes do computador'):
            return self.desktop.system_info()
        if value in ('/processos', 'mostre os processos'):
            return self.desktop.processes()
        choice = re.fullmatch(r'/app (\d+)', value)
        if choice:
            return self.desktop.open_choice(int(choice[1]))
        if re.fullmatch(r'(?:/abrir|abra|abre|abrir|inicie|iniciar|execute|executar) (?:a |o )?(?:(?:aplicativo|programa) )?steam', value):
            return open_steam()
        match = re.fullmatch(r'(?:/abrir|abra|abre|abrir) (?:o )?(?:resultado |item )?(\d+)[.!?]?', value)
        if match:
            return self.open_result(int(match[1]))
        if re.fullmatch(r'(?:abra|abre) o primeiro(?: resultado)?[.!?]?', value):
            return self.open_result(1)
        match = re.fullmatch(r'/localizar (\d+)', value)
        if match:
            return self.open_result(int(match[1]), locate=True)
        match = re.fullmatch(r'(?:/buscar|busque|buscar|procure|procura|encontre|ache) (.+)', value)
        if match:
            query = match[1].strip().rstrip('?!')
            everywhere = False
            if query.startswith('tudo '):
                everywhere, query = True, query[5:]
            for suffix in (' em todo o computador', ' no computador inteiro', ' em todos os discos'):
                if query.endswith(suffix):
                    everywhere, query = True, query[:-len(suffix)]
            query = re.sub(r'^(?:(?:o|a|meu|minha|um|uma) )?(?:arquivo|pasta) (?:chamad[oa] )?', '', query)
            query = re.sub(r'^(?:meu|minha) ', '', query)
            return self.search(query.strip(' "'), everywhere)
        match = re.fullmatch(r'(?:/abrir|abra|abre|abrir|inicie|iniciar|execute|executar) (.+)', value)
        if match:
            query = re.sub(r'^(?:o |a )?(?:meu |minha )?(?:arquivo |pasta )?', '', match[1])
            explicit_file = bool(re.search(r'\b(arquivo|pasta)\b', match[1]))
            query = re.sub(r'^(?:aplicativo|programa) ', '', query)
            if not explicit_file and os.name == 'nt':
                if self.desktop.matches(query):
                    return self.desktop.open_app(query)
            return 'Não identifiquei um aplicativo com esse nome. Vou buscar arquivos e pastas.\n' + self.search(query)
        if value in ('/buscar', 'procure', 'busque'):
            return 'Exemplo: /buscar currículo ou /buscar tudo currículo'
        return None
