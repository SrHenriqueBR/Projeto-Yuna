"""Conversa da Yuna no navegador, servida somente no próprio computador."""
import argparse
from contextlib import closing
import json
import mimetypes
from pathlib import Path
import secrets
import sqlite3
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from http.cookies import SimpleCookie, CookieError
from urllib.parse import urlsplit
import webbrowser

from model_config import load_selected_model
from yuna_governance import Governance

ROOT = Path(__file__).resolve().parent
PORT = 8787
WEB_CONTEXT = (
    'MODO CHAT WEB LOCAL: nesta interface você conversa e guarda memórias explícitas. '
    'Não há ferramentas para abrir programas, ler tela, câmera, microfone, arquivos '
    'ou pesquisar na web. Não diga que executou essas ações. Para usar as ferramentas '
    'do computador, oriente a pessoa a abrir o aplicativo desktop da Yuna. '
    'Converse com vivacidade, curiosidade e bom humor, sem exagerar nem repetir bordões.'
)
COMPANION_STYLE = (
    'CANTINHO DA YUNA: seja uma personagem feminina acolhedora, espontânea e curiosa. '
    'Fale de si no feminino, com português natural e carinho leve, sem bordões repetidos. '
    'Leve a sério o que a pessoa diz, sem julgá-la nem concordar com tudo só para agradar. '
    'Não invente vivências humanas, sentimentos reais ou lembranças. '
    'Conselhos são possibilidades com motivos; a decisão pertence ao usuário. '
    'Em assuntos de alto impacto, reconheça limites e não invente diagnósticos ou certezas.'
)
CONVERSATION_MODES = {
    'companhia': 'MODO CONVERSAR: troque ideias com leveza e interesse pelo assunto atual. '
                 'Responda ao que foi dito; uma pergunta curta pode ajudar a conversa a continuar.',
    'desabafo': 'MODO DESABAFAR: acolha primeiro o que a pessoa contou, sem minimizar. '
                'Não despeje soluções sem ela pedir. Faça no máximo uma pergunta delicada '
                'para entender melhor ou saber se ela quer sugestões.',
    'conselho': 'MODO PEDIR CONSELHO: entenda a situação e o objetivo antes de aconselhar. '
                'Se faltar contexto, faça uma pergunta. Quando houver contexto, ofereça '
                'duas ou três possibilidades práticas, explicando as diferenças sem impor uma escolha.',
}
ASSETS = {
    '/': 'yuna-preview.html', '/yuna-preview.html': 'yuna-preview.html',
    '/yuna-viva.js': 'yuna-viva.js', '/yuna-chat.js': 'yuna-chat.js',
    '/yuna-portrait.webp': 'yuna-portrait.webp',
    '/yuna-gestao.html': 'yuna-gestao.html', '/yuna-gestao.js': 'yuna-gestao.js',
    '/yuna-learning.js': 'yuna-learning.js',
}


class BusyError(Exception):
    pass


class Conversation:
    def __init__(self, root=ROOT, governance=None):
        self.governance = governance if governance is not None else Governance(root)
        self.root = Path(root).resolve()
        self.path = self.root / 'data' / 'yuna.db'
        self.model = load_selected_model(self.root)
        self.lock = threading.Lock()

    def status(self):
        if 'cloud' in self.model.lower():
            return {'ready': False, 'model': self.model,
                    'detail': 'Escolha um modelo local no instalador da Yuna.'}
        try:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open('http://127.0.0.1:11434/api/tags', timeout=2) as response:
                data = json.loads(response.read(1024 * 1024))
            models = {item.get('name') for item in data['models'] if isinstance(item, dict)}
            ready = self.model in models or self.model + ':latest' in models
            return {'ready': ready, 'model': self.model, 'detail': (
                'Pronta para conversar.' if ready else
                f'Baixe o modelo no terminal: ollama pull {self.model}')}
        except (OSError, ValueError, KeyError, TypeError):
            return {'ready': False, 'model': self.model,
                    'detail': 'Abra o aplicativo Ollama e clique em Reconectar.'}

    def history(self):
        if not self.path.is_file():
            return []
        with closing(sqlite3.connect(self.path.as_uri() + '?mode=ro', uri=True)) as db:
            exists = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='messages'").fetchone()
            if not exists:
                return []
            rows = db.execute("SELECT role, content FROM messages WHERE role IN ('user','assistant') ORDER BY id DESC LIMIT 40").fetchall()
        return [{'role': role, 'content': text} for role, text in reversed(rows)]

    def reply(self, message, mode='companhia'):
        if mode not in CONVERSATION_MODES:
            raise ValueError('Modo de conversa desconhecido.')
        if not self.lock.acquire(blocking=False):
            raise BusyError('A Yuna está respondendo a outra mensagem. Aguarde um instante.')
        try:
            from yuna import Memory, respond
            from natural_memory import parse_memory_intent, memory_response
            memory = Memory(self.path)
            try:
                memory.affect.observe(message)
                intent = parse_memory_intent(message)
                answer = memory_response(memory, intent) if intent else None
                if answer is not None:
                    memory.save_turn(message, answer)
                    return answer
                note = '\n'.join((WEB_CONTEXT, COMPANION_STYLE, CONVERSATION_MODES[mode])) + self.governance.reference_context()
                return respond(memory, message, system_note=note, allow_research=False)
            finally:
                memory.close()
        finally:
            self.lock.release()


class YunaServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, root=ROOT, engine=None):
        if address[0] != '127.0.0.1':
            raise ValueError('O chat web deve escutar apenas em 127.0.0.1.')
        self.root = Path(root).resolve()
        self.governance = Governance(root)
        self.engine = engine if engine is not None else Conversation(root, self.governance)
        self.token = secrets.token_urlsafe(32)
        super().__init__(address, Handler)


class Handler(BaseHTTPRequestHandler):
    server_version = 'YunaWeb/1.0'

    def log_message(self, *_):
        # Nunca registrar o conteúdo das conversas.
        pass

    def valid_host(self):
        port = self.server.server_port
        return self.headers.get('Host') in {f'127.0.0.1:{port}', f'localhost:{port}'}

    def valid_origin(self):
        origin = self.headers.get('Origin')
        return origin is None or origin == 'http://' + self.headers.get('Host', '')

    def send(self, status, content, mime='application/json; charset=utf-8', extra_headers=None):
        if not isinstance(content, bytes):
            content = json.dumps(content, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
        for key, value in (extra_headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        try:
            self.wfile.write(content)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        if not self.valid_host() or not self.valid_origin():
            self.send(403, {'error': 'Acesso permitido apenas pela página local da Yuna.'})
            return
        route = urlsplit(self.path).path
        if route == '/favicon.ico':
            self.send(204, b'')
        elif route == '/api/status':
            self.send(200, {**self.server.engine.status(), 'token': self.server.token})
        elif route == '/api/governance':
            self.send(200, {'owner': self.server.governance.owner(), 'token': self.server.token,
                            'scope': 'local', 'remote_access': False})
        elif route == '/api/admin/state':
            if not self.server.governance.authenticated(self.owner_token()):
                self.send(401, {'error': 'Entre com a senha do responsável.'})
                return
            self.send(200, {**self.server.governance.dashboard(),
                            'owner': self.server.governance.owner(),
                            'scope': 'local', 'remote_access': False})
        elif route == '/api/history':
            if not secrets.compare_digest(self.headers.get('X-Yuna-Token', ''), self.server.token):
                self.send(403, {'error': 'Reabra a página local da Yuna.'})
                return
            try:
                self.send(200, {'messages': self.server.engine.history()})
            except sqlite3.Error:
                self.send(503, {'error': 'A memória está ocupada. Tente novamente.'})
        elif route in ASSETS:
            path = self.server.root / 'docs' / ASSETS[route]
            try:
                data = path.read_bytes()
            except OSError:
                self.send(404, {'error': 'Arquivo da interface ausente. Atualize a pasta docs completa.'})
                return
            mime = mimetypes.guess_type(path.name)[0] or 'application/octet-stream'
            if path.suffix == '.mjs':
                mime = 'text/javascript'
            self.send(200, data, mime + ('; charset=utf-8' if path.suffix in {'.html', '.js', '.mjs'} else ''))
        else:
            self.send(404, {'error': 'Página não encontrada.'})

    def owner_token(self):
        try:
            cookies = SimpleCookie()
            cookies.load(self.headers.get('Cookie', ''))
            return cookies['YunaOwner'].value if 'YunaOwner' in cookies else ''
        except CookieError:
            return ''

    def do_POST(self):
        if not self.valid_host() or not self.valid_origin() or not secrets.compare_digest(
                self.headers.get('X-Yuna-Token', ''), self.server.token):
            self.send(403, {'error': 'Reabra a página local da Yuna para conectar.'})
            return
        route = urlsplit(self.path).path
        if route not in ('/api/chat', '/api/learning/propose', '/api/learning/withdraw', '/api/learning/status', '/api/admin/login',
                         '/api/admin/logout', '/api/admin/review'):
            self.send(404, {'error': 'Ação não encontrada.'})
            return
        if self.headers.get_content_type() != 'application/json':
            self.send(415, {'error': 'Use uma mensagem JSON.'})
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 65536:
                self.send(413, {'error': 'Divida essa mensagem em partes menores.'})
                return
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError()
        except (ValueError, UnicodeDecodeError):
            self.send(400, {'error': 'A mensagem não pôde ser lida. Tente novamente.'})
            return
        if route == '/api/chat':
            self.chat(payload)
            return
        store = self.server.governance
        try:
            if route == '/api/learning/propose':
                proposal = store.propose(payload.get('text'), payload.get('consent'), payload.get('owner_id'))
                self.send(201, {**proposal, 'status': 'pending',
                                'message': 'Texto compartilhado nesta instalação e aguardando revisão.'})
            elif route == '/api/learning/withdraw':
                store.withdraw(payload.get('id'), payload.get('receipt'))
                self.send(200, {'ok': True, 'status': 'withdrawn'})
            elif route == '/api/learning/status':
                self.send(200, {'status': store.own_status(payload.get('id'), payload.get('receipt'))})
            elif route == '/api/admin/login':
                token = store.login(payload.get('password'))
                self.send(200, {'ok': True}, extra_headers={
                    'Set-Cookie': f'YunaOwner={token}; HttpOnly; SameSite=Strict; Path=/api/admin; Max-Age=1800'})
            elif route == '/api/admin/logout':
                store.logout(self.owner_token())
                self.send(200, {'ok': True}, extra_headers={
                    'Set-Cookie': 'YunaOwner=; HttpOnly; SameSite=Strict; Path=/api/admin; Max-Age=0'})
            elif route == '/api/admin/review':
                if not store.authenticated(self.owner_token()):
                    raise PermissionError('Entre com a senha do responsável.')
                ident, decision = payload.get('id'), payload.get('decision')
                if not isinstance(ident, str) or len(ident) > 80 or not isinstance(decision, str):
                    raise ValueError('Pedido de revisão inválido.')
                store.review(ident, decision)
                self.send(200, {'ok': True})
        except PermissionError as error:
            self.send(401, {'error': str(error)})
        except ValueError as error:
            self.send(400, {'error': str(error)})
        except sqlite3.Error:
            self.send(503, {'error': 'A gestão está ocupada. Tente novamente.'})

    def chat(self, payload):
        message = payload.get('message')
        mode = payload.get('mode', 'companhia')
        if not isinstance(message, str) or not message.strip():
            self.send(400, {'error': 'Escreva uma mensagem antes de enviar.'})
            return
        if not isinstance(mode, str) or mode not in CONVERSATION_MODES:
            self.send(400, {'error': 'Escolha Conversar, Desabafar ou Pedir conselho.'})
            return
        try:
            answer = self.server.engine.reply(message.strip(), mode=mode)
            if not isinstance(answer, str) or not answer.strip():
                raise RuntimeError('O modelo retornou uma resposta vazia. Tente novamente.')
            self.send(200, {'answer': answer})
        except BusyError as error:
            self.send(409, {'error': str(error)})
        except RuntimeError as error:
            self.send(503, {'error': str(error)})
        except Exception:
            self.send(500, {'error': 'Não consegui concluir a resposta. Verifique o Ollama e tente novamente.'})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=PORT)
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    try:
        server = YunaServer(('127.0.0.1', args.port))
    except (OSError, OverflowError) as error:
        print(f'Não foi possível abrir o chat local na porta {args.port}: {error}')
        return 1
    url = f'http://127.0.0.1:{server.server_port}/'
    print(f'Yuna Web: {url}\nMantenha esta janela aberta. Ctrl+C encerra o chat web.')
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
