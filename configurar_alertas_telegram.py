"""Descubra o chat ID privado do seu bot SEM colocar token em URL do navegador.

Rode localmente: py -3 configurar_alertas_telegram.py
Não salva token, chat, mensagens, nomes ou arquivos.
"""
from getpass import getpass
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from free_telegram_alerts import validate_bot_token, TelegramConfigurationError


def list_private_chat_ids(token, *, opener=urlopen):
    validated = validate_bot_token(token)
    request = Request(
        "https://api.telegram.org/bot" + validated + "/getUpdates?limit=30&timeout=0",
        headers={"Accept": "application/json"},
        method="GET",
    )
    try:
        with opener(request, timeout=8) as response:
            value = json.loads(response.read(16384).decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, ValueError):
        raise RuntimeError(
            "Não consegui consultar o bot. Confira o token e envie /start "
            "ao bot no Telegram. Não compartilhe o token."
        ) from None
    if not isinstance(value, dict) or value.get("ok") is not True:
        raise RuntimeError(
            "O Telegram não autorizou a consulta. Verifique o token."
        )
    result = value.get("result")
    if not isinstance(result, list):
        raise RuntimeError("Resposta do Telegram não reconhecida.")
    ids = set()
    for event in result:
        if not isinstance(event, dict):
            continue
        message = event.get("message")
        if not isinstance(message, dict):
            continue
        chat = message.get("chat")
        if not isinstance(chat, dict) or chat.get("type") != "private":
            continue
        identifier = chat.get("id")
        if isinstance(identifier, int) and identifier > 0:
            ids.add(identifier)
    return sorted(ids)


def main():
    print("Yuna — localizar chat ID privado para alertas gratuitos")
    print("1. Abra seu bot no Telegram do celular e envie /start.")
    print("2. Cole abaixo o token criado no BotFather (entrada oculta).")
    token = getpass("Token do bot: ")
    try:
        chats = list_private_chat_ids(token)
    except (RuntimeError, TelegramConfigurationError) as exc:
        print("Falha: " + str(exc))
        return 1
    if not chats:
        print("Nenhum chat privado encontrado. Envie /start ao bot e tente novamente.")
        return 1
    print("Chats privados encontrados (confirme qual é o seu no Telegram):")
    for chat_id in chats:
        print("  " + str(chat_id))
    print("Copie APENAS o ID correto para a janela Modo Segurança da Yuna.")
    print("Seu token não foi salvo. Não publique o ID ou token.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
