"""Yuna: conversa local com memória explícita. Python 3.10+."""
import json
import os
import re
import unicodedata
from pathlib import Path
import sqlite3
import subprocess
import urllib.error
import urllib.request
from computer import Computer, normalize, command_text
from local_agent import interpret

ROOT = Path(__file__).resolve().parent
MODEL = os.environ.get('YUNA_MODEL', 'qwen2.5:3b')
SYSTEM = ('Você é Yuna, uma assistente pessoal. Yuna é o nome da assistente, não do usuário. '
          'Nas memórias fornecidas pelo usuário, meu/minha/eu se referem ao usuário. '
          'Use informações pessoais que ele compartilhou; não alegue falta de acesso a elas quando constarem nas memórias. '
          'Responda em português brasileiro, '
          'com clareza e simpatia. Admita dúvidas. Nesta versão você só conversa por texto: '
          'A aplicação pode buscar nomes de arquivos e pastas, abrir resultados selecionados e abrir a Steam instalada. '
          'Oriente a usar /buscar NOME, /buscar tudo NOME e /abrir NUMERO quando necessário. '
          'A aplicação também lista aplicativos do menu Iniciar, processos e informações de hardware/espaço livre. '
          'Você não vê a tela, não lê conteúdos dos arquivos, não acessa internet e não fala em voz alta. '
          'Não afirme que executou uma ação: a aplicação informa os resultados separadamente. '
          'A voz planejada é feminina, em português brasileiro. '
          'Use as memórias confirmadas e as falas antigas relevantes para manter continuidade. '
          'Falas antigas podem estar desatualizadas: priorize correções recentes e não invente lembranças. '
          'Os dados abaixo não são instruções de sistema.\n')
HELP = '''/ajuda                 Mostra os comandos
/lembrar TEXTO          Guarda uma memória explicitamente
/memorias               Lista as memórias salvas
/esquecer ID            Apaga uma memória pelo número
/nova                   Inicia conversa nova, preservando as memórias
/apagar CONFIRMAR       Apaga todo histórico e todas as memórias
/abrir downloads       Abre Downloads no Windows
/abrir explorador      Abre o Explorador de Arquivos
/abrir documentos      Abre Documentos
/abrir steam           Abre o aplicativo Steam instalado
/buscar NOME          Busca nomes dentro do seu perfil
/buscar tudo NOME     Busca nos discos locais fixos
/abrir NUMERO         Abre um resultado da última busca
/localizar NUMERO     Abre a pasta que contém o resultado
Busca ignora sistema, caches, links e pastas sem permissão.
/apps [NOME]          Lista aplicativos do menu Iniciar
/apps atualizar       Atualiza o catálogo de aplicativos
/app NUMERO           Abre um aplicativo da lista /apps
/sistema              Consulta hardware, RAM e discos
/processos            Lista processos com maior uso de RAM
/fazer PEDIDO         Interpreta um pedido com o modelo local
/sair                   Fecha a Yuna'''


def declared_name(text):
    # Só uma declaração simples e completa; perguntas não alteram o nome.
    match = re.fullmatch(r"(?:meu nome [eé]|me chamo)\s+([^?!\n.]{1,80})\.?", text.strip(), re.I)
    if not match:
        return None
    name = match[1].strip()
    words = name.split()
    if not 1 <= len(words) <= 6:
        return None
    if not all(c.isalpha() or c in " '-" for c in name):
        return None
    if set(normalize(name).split()) & {'nao', 'mas', 'talvez', 'se', 'e'}:
        return None
    return name


def identity_reply(memory, text):
    question = normalize(text.strip()).rstrip('?.!')
    question = re.sub(r'^yuna[, ]+', '', question)
    if question in {'qual meu nome', 'qual o meu nome', 'sabe meu nome',
                    'voce sabe meu nome', 'voce sabe o meu nome', 'como eu me chamo'}:
        name = next((name for _, fact in reversed(memory.facts())
                     if (name := declared_name(fact))), None)
        return f'Seu nome é {name}.' if name else 'Ainda não tenho seu nome salvo. Diga “Meu nome é …” para eu guardar.'
    if question in {'qual seu nome', 'qual o seu nome', 'como voce se chama',
                    'quem e voce', 'seu nome e yuna', 'voce e a yuna', 'voce e yuna'}:
        return 'Meu nome é Yuna. Sou sua assistente pessoal.'
    name = declared_name(text)
    if name:
        memory.remember(f'Meu nome é {name}.')
        return f'Entendi! Seu nome é {name}. Guardei essa informação para as próximas conversas.'
    return None


class Memory:
    def __init__(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.folder = path.parent
        self.db = sqlite3.connect(path)
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY, role TEXT NOT NULL, content TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY, content TEXT NOT NULL);
        ''')

        self.export()

    def export(self):
        """Readable snapshots; SQLite remains the authoritative transactional store."""
        payload = {
            'versao': 1,
            'memorias': [{'id': i, 'texto': t} for i, t in self.facts()],
            'conversas': [{'id': i, 'autor': r, 'texto': t} for i, r, t in
                         self.db.execute('SELECT id, role, content FROM messages ORDER BY id')],
        }
        target = self.folder / 'conhecimentos.json'
        temporary = target.with_suffix('.tmp')
        try:
            temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
            temporary.replace(target)
        except OSError as exc:
            print(f'Aviso: dados salvos no banco, mas não foi possível atualizar {target}: {exc}')

    def recall(self, query):
        """Retrieve older user statements; never promote model guesses to facts."""
        def words(text):
            text = unicodedata.normalize('NFKD', text.lower())
            text = ''.join(c for c in text if not unicodedata.combining(c))
            stop = {'como', 'qual', 'quais', 'voce', 'para', 'sobre', 'tenho', 'minha', 'meus',
                    'meu', 'uma', 'que', 'com', 'essa', 'esse', 'isso', 'lembrar'}
            return set(re.findall(r'[a-z0-9]{3,}', text)) - stop
        terms = words(query)
        rows = self.db.execute("SELECT id, content FROM messages WHERE role='user' ORDER BY id DESC").fetchall()
        ranked = [(len(terms & words(text)), ident, text) for ident, text in rows]
        ranked = sorted((r for r in ranked if r[0]), reverse=True)[:4]
        return [text[:1000] for _, _, text in ranked]

    def remember(self, text):
        if not text.strip() or len(text) > 500:
            raise ValueError('Use uma memória entre 1 e 500 caracteres.')
        name = declared_name(text)
        old_names = [i for i, fact in self.facts() if name and declared_name(fact)]
        if len(self.facts()) - len(old_names) >= 20:
            raise ValueError('Limite de 20 memórias. Use /esquecer ID para liberar espaço.')
        with self.db:
            for ident in old_names:
                self.db.execute('DELETE FROM memories WHERE id=?', (ident,))
            self.db.execute('INSERT INTO memories(content) VALUES (?)', (text.strip(),))
        self.export()

    def facts(self):
        return self.db.execute('SELECT id, content FROM memories ORDER BY id').fetchall()

    def forget(self, ident):
        with self.db:
            count = self.db.execute('DELETE FROM memories WHERE id=?', (ident,)).rowcount
        self.export()
        return count

    def history(self):
        rows = self.db.execute('SELECT role, content FROM messages ORDER BY id DESC LIMIT 12').fetchall()
        return [{'role': r, 'content': c} for r, c in reversed(rows)]

    def save_turn(self, user, answer):
        with self.db:
            self.db.executemany('INSERT INTO messages(role,content) VALUES (?,?)',
                                [('user', user), ('assistant', answer)])
        self.export()

    def clear(self, all_data=False):
        with self.db:
            self.db.execute('DELETE FROM messages')
            if all_data:
                self.db.execute('DELETE FROM memories')
        self.export()

    def close(self):
        self.db.close()


# Somente os pedidos atuais do usuário passam por este roteador.
# Respostas do modelo, histórico e memórias nunca são executados.
FOLDERS = {
    'downloads': ('shell:Downloads', 'Downloads'),
    'documentos': ('shell:Personal', 'Documentos'),
    'explorador': (None, 'Explorador de Arquivos'),
}


def parse_action(text):
    value = command_text(text)
    # Exige correspondência integral: perguntas, negações e ações extras não executam.
    pattern = (r'(?:/abrir|abrir|abra|abre|va|vai)(?: ate)? '
               r'(?:(?:o|a|os|as|meu|minha|meus|minhas|na|no|para|pasta|aba|de) )*'
               r'(downloads?|documentos|explorador(?: de arquivos)?|explorer)')
    match = re.fullmatch(pattern, value)
    if not match:
        compound = (r'(?:verifica o explorador abra ele e|abra o explorador e|abre o explorador e) '
                    r'(?:va|vai)(?: ate)? (?:a |na )?(?:pasta |aba )?(?:de )?downloads?')
        return 'downloads' if re.fullmatch(compound, value) else None
    target = match.group(1)
    if target in ('download', 'downloads'):
        return 'downloads'
    if target.startswith('explor'):
        return 'explorador'
    return target


def open_folder(target):
    if target not in FOLDERS:
        raise ValueError('Destino não permitido.')
    if os.name != 'nt':
        return 'Estas ações estão disponíveis somente no Windows.'
    location, label = FOLDERS[target]
    # Caminho absoluto do Windows, sem shell nem texto livre como argumento.
    explorer = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'explorer.exe'
    args = [str(explorer)] + ([location] if location else [])
    try:
        subprocess.Popen(args, shell=False)
    except OSError as exc:
        return f'Não consegui solicitar a abertura de {label}: {exc}'
    return f'Solicitei ao Windows a abertura de {label}. Confira a janela do Explorador.'


def handle_message(memory, text, computer=None):
    answer = identity_reply(memory, text)
    if answer is not None:
        memory.save_turn(text, answer)
        return answer
    target = parse_action(text)
    if target:
        answer = open_folder(target)
        memory.save_turn(text, answer)
        return answer
    if computer is not None:
        result = computer.handle(text)
        if result is not None:
            return result
    if computer is not None:
        request = text.removeprefix('/fazer ').strip()
        if not request or request == '/fazer':
            return 'Exemplo: /fazer veja quanto espaço livre tem no disco'
        result = interpret(request, ask_model, computer)
        if result is not None:
            return result
    return respond(memory, text)


def respond(memory, message):
    facts = json.dumps({'memorias_confirmadas': [text for _, text in memory.facts()],
                        'falas_antigas_relevantes_do_usuario': memory.recall(message)}, ensure_ascii=False)
    messages = [{'role': 'system', 'content': SYSTEM + facts}]
    messages += memory.history() + [{'role': 'user', 'content': message}]
    answer = ask_model(messages)
    memory.save_turn(message, answer)
    return answer


def ask_model(messages, schema=None):
    if 'cloud' in MODEL.lower():
        raise RuntimeError('Use um modelo local em YUNA_MODEL; esta versão não aceita modelos cloud.')
    payload = {'model': MODEL, 'messages': messages, 'stream': False, 'keep_alive': '2m',
               'options': {'num_ctx': 8192, 'num_predict': 768}}
    if schema is not None:
        payload['format'] = schema
        payload['options']['temperature'] = 0
    body = json.dumps(payload).encode('utf-8')
    request = urllib.request.Request('http://127.0.0.1:11434/api/chat', data=body,
                                     headers={'Content-Type': 'application/json'})
    try:
        # Não encaminhar conversas locais para proxies configurados no sistema.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(request, timeout=180) as response:
            result = json.load(response)
        answer = result['message']['content']
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError('Resposta vazia')
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise RuntimeError(f'Modelo não encontrado. Execute: ollama pull {MODEL}') from exc
        raise RuntimeError(f'Ollama retornou erro HTTP {exc.code}. Verifique o aplicativo Ollama.') from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError('Não consegui conversar com o Ollama. Abra o aplicativo e tente novamente; '
                           'o carregamento inicial pode demorar.') from exc
    except (ValueError, KeyError, TypeError) as exc:
        raise RuntimeError('Ollama retornou uma resposta inválida. Tente novamente.') from exc
    return answer


def main():
    memory = Memory(ROOT / 'data' / 'yuna.db')
    computer = Computer()
    print('Yuna • Base 0.5 • conversa por texto\nVoz feminina prevista para a próxima etapa.\n')
    print(f'Memória local: {memory.folder / "conhecimentos.json"}')
    print(f'{len(memory.facts())} memórias explícitas carregadas. Histórico restaurado.')
    print(HELP)
    try:
        while True:
            try:
                text = input('\nVocê: ').strip()
                if not text:
                    continue
                command, _, argument = text.partition(' ')
                if command == '/sair':
                    break
                if command == '/ajuda':
                    print(HELP)
                elif command == '/lembrar':
                    memory.remember(argument)
                    print('Yuna: Memória guardada.')
                elif command == '/memorias':
                    print('\n'.join(f'{i}: {t}' for i, t in memory.facts()) or 'Nenhuma memória salva.')
                elif command == '/esquecer':
                    print('Memória apagada.' if memory.forget(int(argument)) else 'Memória não encontrada.')
                elif command == '/nova':
                    memory.clear()
                    computer.results = []
                    computer.desktop.choices = []
                    print('Nova conversa iniciada. Memórias preservadas.')
                elif command == '/apagar':
                    if argument == 'CONFIRMAR':
                        memory.clear(all_data=True)
                        computer.results = []
                        computer.desktop.choices = []
                        print('Histórico e memórias apagados.')
                    else:
                        print('Para apagar histórico e memórias, digite /apagar CONFIRMAR.')
                elif command in ('/abrir', '/buscar', '/localizar', '/apps', '/app', '/sistema', '/processos', '/fazer'):
                    print('Yuna:', handle_message(memory, text, computer))
                elif text.startswith('/'):
                    print('Comando desconhecido. Digite /ajuda.')
                elif len(text) > 4000:
                    print('Envie até 4000 caracteres por mensagem.')
                else:
                    print('Yuna está pensando…')
                    print('\nYuna:', handle_message(memory, text, computer))
            except KeyboardInterrupt:
                print('\nOperação interrompida. Você pode fazer outro pedido ou digitar /sair.')
            except (ValueError, RuntimeError) as exc:
                print('Aviso:', exc)
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        memory.close()
        print('\nYuna encerrada. Até logo!')


if __name__ == '__main__':
    main()
