"""Resposta incremental do Ollama local, com cancelamento da conexão em curso.

Protocolo: https://docs.ollama.com/api/chat — NDJSON e evento final done=true.
Só message.content é exposto; thinking e tool_calls nunca são apresentados/executados.
"""
import http.client
import io
import json
import socket
from threading import Event, Thread
from time import monotonic

from action_diagnostics import LocalModelError

MAX_LINE = 128 * 1024
MAX_WIRE = 8 * 1024 * 1024
MAX_TEXT = 96000


class _PollingReader(io.RawIOBase):
    """Espera curta no socket sem invalidar o buffer HTTP a cada timeout.

    shutdown de outra thread nem sempre acorda recv no Windows. A leitura
    verifica cancelamento mesmo quando o servidor fica completamente parado.
    A cópia mantém o socket vivo quando HTTPConnection recebe Connection: close.
    """
    def __init__(self, transport, check):
        super().__init__()
        self._transport = transport.dup()
        self._transport.settimeout(.1)
        self._check = check

    def readable(self):
        return True

    def readinto(self, buffer):
        self._checkClosed()
        while True:
            self._check()
            try:
                return self._transport.recv_into(buffer)
            except socket.timeout:
                # O timeout é tratado antes de chegar ao BufferedReader;
                # fragmentos já recebidos permanecem íntegros no buffer.
                continue

    def close(self):
        try:
            if hasattr(self, "_transport"):
                self._transport.close()
        finally:
            super().close()


class _ResponseSocket:
    def __init__(self, transport, check):
        self._transport = transport
        self._check = check

    def makefile(self, mode):
        if mode != "rb":
            raise ValueError("A resposta HTTP exige leitura binária.")
        return io.BufferedReader(_PollingReader(self._transport, self._check))


def chat_stream(payload, *, on_text=None, on_phase=None, cancelled=None, timeout=300):
    """Retorna apenas uma resposta final íntegra. Parcial nunca equivale a sucesso."""
    cancelled = cancelled or (lambda: False)
    on_phase = on_phase or (lambda text: None)
    if cancelled():
        raise InterruptedError("Resposta cancelada.")
    connection = http.client.HTTPConnection("127.0.0.1", 11434, timeout=5)
    finished = Event()
    interrupted = Event()
    expired = Event()
    deadline = monotonic() + timeout
    transport = None
    watcher = None
    response = None

    def check():
        if cancelled() or interrupted.is_set():
            raise InterruptedError("Resposta cancelada.")
        if expired.is_set() or monotonic() >= deadline:
            raise TimeoutError("Tempo total da resposta excedido.")

    def watch():
        # Encerra também escritas pendentes. A leitura tem seu próprio polling
        # porque shutdown de outra thread não é suficiente em todo Windows.
        while not finished.wait(.08):
            if cancelled():
                interrupted.set()
            elif monotonic() >= deadline:
                expired.set()
            else:
                continue
            try:
                transport.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            return

    try:
        on_phase("Conectando ao Ollama…")
        connection.connect()
        transport = connection.sock
        transport.settimeout(min(timeout, 5))
        connection.response_class = lambda sock, *args, **kwargs: http.client.HTTPResponse(
            _ResponseSocket(sock, check), *args, **kwargs)
        check()
        watcher = Thread(target=watch, daemon=True, name="Yuna-cancelar-resposta")
        watcher.start()
        on_phase("Aguardando o modelo local…")
        body = json.dumps(dict(payload, stream=True)).encode("utf-8")
        connection.request("POST", "/api/chat", body=body,
                           headers={"Content-Type": "application/json", "Accept": "application/x-ndjson"})
        response = connection.getresponse()
        check()
        if response.status == 404:
            raise LocalModelError(f'Modelo local não encontrado. Prepare {payload["model"]} na Central da Yuna.')
        if response.status != 200:
            # HTTPConnection não segue redirecionamentos nem consulta proxies do sistema.
            raise LocalModelError(f"Ollama retornou erro HTTP {response.status}. Verifique o aplicativo Ollama.")
        pieces = []
        chars = wire = 0
        last_emit = 0.0
        emitted = ""
        phase = ""
        while True:
            check()
            line = response.readline(MAX_LINE + 1)
            check()
            if not line:
                raise LocalModelError("A conexão com o Ollama terminou antes da resposta completa. Tente novamente.")
            wire += len(line)
            if len(line) > MAX_LINE or wire > MAX_WIRE:
                raise LocalModelError("O Ollama excedeu o limite de dados desta resposta. Divida o pedido.")
            if not line.strip():
                continue
            event = json.loads(line)
            if not isinstance(event, dict) or "error" in event:
                raise LocalModelError("O Ollama interrompeu a resposta. Confira o modelo na Central.")
            message = event.get("message", {})
            if not isinstance(message, dict):
                raise ValueError("Mensagem inválida")
            chunk = message.get("content", "")
            if not isinstance(chunk, str):
                raise ValueError("Conteúdo inválido")
            if chunk:
                chars += len(chunk)
                if chars > MAX_TEXT:
                    raise LocalModelError("A resposta ficou grande demais. Divida o pedido em partes menores.")
                pieces.append(chunk)
                new_phase = "Escrevendo a resposta…"
            elif not pieces:
                new_phase = "Preparando a resposta…"
            else:
                new_phase = phase
            if new_phase != phase:
                phase = new_phase
                on_phase(phase)
            done = event.get("done") is True
            now = monotonic()
            if on_text is not None and pieces and (done or now - last_emit >= .08):
                content = "".join(pieces)
                if content != emitted:
                    check()
                    on_text(content)
                    emitted = content
                    last_emit = now
            if done:
                check()
                return {"message": {"content": "".join(pieces)},
                        "done": True, "done_reason": event.get("done_reason")}
    except (OSError, http.client.HTTPException):
        check()
        raise LocalModelError("Não consegui manter a conexão com o Ollama. Abra o aplicativo e tente novamente.") from None
    except (ValueError, KeyError, TypeError):
        check()
        raise LocalModelError("Ollama retornou dados inválidos durante a resposta. Tente novamente.") from None
    finally:
        finished.set()
        if watcher is not None:
            watcher.join(timeout=.3)
        if response is not None:
            response.close()
        connection.close()
