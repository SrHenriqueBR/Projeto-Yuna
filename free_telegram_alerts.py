"""Alertas de segurança por Telegram Bot API, gratuitos no uso normal.

Somente envia rótulos fechados de eventos (SOS e som alto) após opt-in
local explícito. Nunca envia áudio, vídeo, frames ou texto da conversa.
Não habilita 'paid broadcast' nem canais pagos; limites baixos por sessão.
O token fica em memória durante a sessão e NUNCA deve ser registrado.
"""
import json
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from home_safety import SAFETY_EVENTS

_TOKEN_PATTERN = re.compile(r"[1-9][0-9]{5,14}:[A-Za-z0-9_-]{30,100}\Z")
_PRIVATE_CHAT_PATTERN = re.compile(r"[1-9][0-9]{0,18}\Z")

# Só os tipos de evento predefinidos podem sair do computador.
_EVENT_MESSAGES = {
    "sos": (
        "🆘 Yuna — SOS manual acionado no notebook monitorado. "
        "Entre em contato imediatamente para conferir a situação. "
        "O alerta não confirma uma emergência."
    ),
    "som_alto": (
        "⚠️ Yuna — som alto e persistente detectado no notebook monitorado. "
        "Pode ser televisão, música ou falso alarme. "
        "Entre em contato para conferir se está tudo bem."
    ),
}
assert set(_EVENT_MESSAGES) == set(SAFETY_EVENTS)


class TelegramConfigurationError(ValueError):
    """Falta configuração ou identificação de destinatário."""


class TelegramSendError(RuntimeError):
    """Não foi possível confirmar aceite pela API; entrega não garantida."""


def validate_bot_token(token):
    if not isinstance(token, str) or not _TOKEN_PATTERN.fullmatch(token.strip()):
        raise TelegramConfigurationError("Token do bot Telegram inválido")
    return token.strip()


def validate_private_chat_id(chat_id):
    """Aceita apenas chat privado positivo, nunca grupos nem canais."""
    raw = str(chat_id).strip() if isinstance(chat_id, (str, int)) else ""
    if not _PRIVATE_CHAT_PATTERN.fullmatch(raw):
        raise TelegramConfigurationError(
            "Informe o identificador numérico de uma conversa privada"
        )
    return raw


class FreeTelegramNotifier:
    """Transporte estritamente gratuito: nenhum parâmetro de broadcast pago."""

    def __init__(self, token, chat_id):
        self._token = validate_bot_token(token)
        self._chat_id = validate_private_chat_id(chat_id)

    def send_event(self, kind, *, opener=urlopen):
        if kind not in _EVENT_MESSAGES:
            raise ValueError("Somente eventos SOS ou som alto podem ser enviados")
        endpoint = (
            "https://api.telegram.org/bot" + self._token + "/sendMessage"
        )
        body = {
            "chat_id": self._chat_id,
            "text": _EVENT_MESSAGES[kind],
            "disable_notification": False,
            "protect_content": True,
            "allow_paid_broadcast": False,
        }
        request = Request(
            endpoint,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Accept": "application/json",
                "Cache-Control": "no-store",
            },
            method="POST",
        )
        try:
            with opener(request, timeout=8) as response:
                # Limite estrito na resposta para não consumir memória
                data = json.loads(response.read(8192).decode("utf-8"))
            if not isinstance(data, dict) or data.get("ok") is not True:
                raise TelegramSendError(
                    "Telegram não confirmou o recebimento da solicitação"
                )
            result = data.get("result")
            if not isinstance(result, dict) or not isinstance(
                    result.get("message_id"), int):
                raise TelegramSendError(
                    "Telegram não retornou confirmação da solicitação"
                )
            # A API aceitou a requisição; NÃO comprova leitura no celular.
            return True
        except (HTTPError, URLError, TimeoutError, OSError, UnicodeError,
                ValueError) as exc:
            # Exceções podem conter URL COM TOKEN e corpo privado.
            # Nunca expor tokens nem URLs em logs, UI ou mensagens.
            raise TelegramSendError(
                "Telegram não confirmou o alerta. Verifique internet, bot "
                "e chat privado autorizado, sem compartilhar seu token."
            ) from None
