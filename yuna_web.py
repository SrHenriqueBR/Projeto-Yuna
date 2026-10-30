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
from urllib.parse import urlsplit
import webbrowser

from model_config import load_selected_model

ROOT = Path(__file__).resolve().parent
PORT = 8787
WEB_CONTEXT = (
    'MODO CHAT WEB LOCAL: nesta interface você conversa e guarda memórias explícitas. '
    'Não há ferramentas para abrir programas, ler tela, câmera, microfone, arquivos '
    'ou pesquisar na web. Não diga que executou essas ações. Para usar as ferramentas '
    'do computador, oriente a pessoa a abrir o aplicativo desktop da Yuna. '
    'Converse com vivacidade, curiosidade e bom humor, sem exagerar nem repetir bordões.'
)
ASSETS = {
    '/': 'yuna-preview.html', '/yuna-preview.html': 'yuna-preview.html',
    '/yuna-viva.js': 'yuna-viva.js', '/yuna-chat.js': 'yuna-chat.js',
    '/yuna-portrait.webp': 'yuna-portrait.webp',
}


class BusyError(Exception):
    pass


class Conversation:
    def __init__(self, root=ROOT):
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

    def reply(self, message):
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
                return respond(memory, message, system_note=WEB_CONTEXT, allow_research=False)
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
        self.engine = engine if engine is not None else Conversation(root)
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

    def send(self, status, content, mime='application/json; charset=utf-8'):
        if not isinstance(content, bytes):
            content = json.dumps(content, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
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

    def do_POST(self):
        if not self.valid_host() or not self.valid_origin() or not secrets.compare_digest(
                self.headers.get('X-Yuna-Token', ''), self.server.token):
            self.send(403, {'error': 'Reabra a página local da Yuna para conectar o chat.'})
            return
        if urlsplit(self.path).path != '/api/chat':
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
            message = payload.get('message') if isinstance(payload, dict) else None
            if not isinstance(message, str) or not message.strip():
                self.send(400, {'error': 'Escreva uma mensagem antes de enviar.'})
                return
        except (ValueError, UnicodeDecodeError):
            self.send(400, {'error': 'A mensagem não pôde ser lida. Tente novamente.'})
            return
        try:
            answer = self.server.engine.reply(message.strip())
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
