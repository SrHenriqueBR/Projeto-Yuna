"""Ações de navegador estritamente permitidas e consulta pública à Wikipédia.

Nenhum script é executado em páginas. Pesquisa abre URL montada pelo aplicativo,
com o texto que a pessoa pediu. Pausar usa tecla global de mídia do Windows.
Não controla todos os sites, players e janelas arbitrariamente.
"""
import ctypes
import html
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import quote, urlencode
import urllib.error
import urllib.request
import webbrowser
from collections import OrderedDict
from threading import Lock
import time
from computer import command_text, normalize

UA = "Projeto-Yuna/0.12 (assistente pessoal; pesquisa pública por solicitação)"
SAFE_SITES = {"youtube": "https://www.youtube.com",
              "google": "https://www.google.com",
              "wikipedia": "https://pt.wikipedia.org"}
_CACHE = OrderedDict()
_CACHE_LOCK = Lock()
_CACHE_SECONDS = 120


def public_search_query(query):
    """Só o texto explicitamente pedido; não acrescentar histórico ou arquivos."""
    if not isinstance(query, str) or not 1 <= len(query.strip()) <= 160:
        raise ValueError("Use uma pesquisa com 1 a 160 caracteres.")
    value = query.strip()
    if re.search(r"(?i)\b(?:senha|password|cpf|token|chave\s+api|pix|endereco\s+pessoal|"
                 r"cartao\s+de\s+credito)\b|[\w.+-]+@[\w.-]+\.[a-z]{2,}|"
                 r"(?:[a-z]:\\|\\\\)|[\r\n\x00]", value):
        raise ValueError("Essa pesquisa pode conter dados privados. Use apenas um assunto público.")
    return value


def _chrome_binary():
    if os.name != "nt":
        return None
    root = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
    alt = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
    local = Path(os.environ.get("LocalAppData", ""))
    for base in (root, alt, local):
        path = base / "Google/Chrome/Application/chrome.exe"
        if path.is_file():
            return path
    return None


def open_allowed_url(url, chrome=False):
    if not any(url == base or url.startswith(base + "/") or url.startswith(base + "?")
               for base in SAFE_SITES.values()):
        raise ValueError("Só abro Google, YouTube ou Wikipédia neste modo.")
    binary = _chrome_binary() if chrome else None
    if binary:
        subprocess.Popen([str(binary), url], shell=False)
        return "Solicitei ao Google Chrome para abrir: " + url
    if webbrowser.open(url):
        return "Solicitei ao navegador padrão para abrir: " + url
    return "Não consegui abrir o navegador. Verifique a configuração do Windows."


def media_key(action):
    keys = {"pause": 0xB3, "play": 0xB3, "next": 0xB0, "previous": 0xB1}
    if os.name != "nt":
        return "Controle de mídia disponível apenas no Windows."
    if action not in keys:
        raise ValueError("Ação de mídia não permitida.")
    key = keys[action]
    ctypes.windll.user32.keybd_event(key, 0, 0, 0)
    ctypes.windll.user32.keybd_event(key, 0, 2, 0)
    return ("Enviei a tecla multimídia do Windows. O resultado depende "
            "de qual aplicativo está reproduzindo mídia; não consigo confirmar o estado.")


def wikipedia_lookup(query):
    if not isinstance(query, str) or not 1 <= len(query.strip()) <= 160:
        raise ValueError("Use uma pesquisa com 1 a 160 caracteres.")
    try:
        query = public_search_query(query)
    except ValueError:
        return "Essa pesquisa pode incluir dados privados; não vou enviá-los à Wikipédia."
    key = query.casefold()
    with _CACHE_LOCK:
        cached = _CACHE.get(key)
        if cached and time.monotonic() - cached[0] < _CACHE_SECONDS:
            _CACHE.move_to_end(key)
            return cached[1] + "\n(Cache local de até 2 minutos.)"
    params = urlencode({"q": query, "limit": 3})
    url = "https://pt.wikipedia.org/w/rest.php/v1/search/page?" + params
    request = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            raw = response.read(256000 + 1)
            if len(raw) > 256000:
                raise ValueError("Resposta de pesquisa muito grande.")
            results = json.loads(raw)
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        return "Não consegui consultar a Wikipédia agora. Tente uma busca no navegador."
    pages = results.get("pages", []) if isinstance(results, dict) else []
    if not isinstance(pages, list) or not pages:
        return "Nenhum resultado encontrado na Wikipédia em português."
    lines = []
    for item in pages[:3]:
        if not isinstance(item, dict):
            continue
        title = item.get("title", "")
        desc = item.get("description", "") or ""
        excerpt = item.get("excerpt", "") or ""
        if not all(isinstance(part, str) for part in (title, desc, excerpt)):
            continue
        excerpt = re.sub(r"<[^>]+>", "", excerpt)
        pageurl = "https://pt.wikipedia.org/wiki/" + quote(str(item.get("key", title)).replace(" ", "_"), safe="")
        lines.append(f"{title}: {html.unescape(desc)}. {html.unescape(excerpt)[:240]}\nFonte: {pageurl}")
    if not lines:
        return "Nenhum resultado válido encontrado na Wikipédia."
    result = "\n\n".join(lines)
    with _CACHE_LOCK:
        _CACHE[key] = (time.monotonic(), result)
        _CACHE.move_to_end(key)
        while len(_CACHE) > 32:
            _CACHE.popitem(last=False)
    return result


def handle_web_command(message, session=None):
    value = command_text(message)
    if re.search(r"\b(nao|nunca)\b", value) or re.match(r"^(?:como|por que|porque|se eu|o que acontece)\b", value):
        return None

    # Web ampla abre resultados no navegador. Não afirmar que leu os sites.
    match = re.fullmatch(r"(?:/web\s+|(?:pesquise|pesquisa|procure|busque)\s+"
                         r"(?:na web|na internet)\s+(?:sobre\s+)?)(.+)", value)
    if match:
        query = public_search_query(match[1])
        opened = open_allowed_url("https://www.google.com/search?" + urlencode({"q": query}),
                                  chrome=bool(getattr(session, "prefer_chrome", False)))
        return opened + "\nOs resultados ficam no navegador; não li o conteúdo dessas páginas."

    if re.fullmatch(r"(?:pausa|pause|pausar|pare|parar)\s*(?:o video|a musica|o som|a reproducao)?", value):
        return media_key("pause")
    if re.fullmatch(r"(?:continua|continue|retoma|retomar|reproduz|play)(?:\s+(?:o video|a musica|a reproducao))?", value):
        return media_key("play")
    if re.fullmatch(r"(?:proxima|proximo)(?:\s+(?:musica|faixa|video))?", value):
        return media_key("next")

    # Buscas explícitas em YouTube ou Google: o conteúdo NÃO é baixado por Yuna.
    match = re.search(r"\b(?:pesquise|pesquisa|pesquisar|procure|buscar|busque)\s+(.+?)"
                      r"\s+(?:no|na)\s+(youtube|google)\s*$", value)
    if match:
        query, engine = public_search_query(match[1]), match[2]
        chrome = ("chrome" in value or bool(getattr(session, "prefer_chrome", False)))
        if engine == "youtube":
            return open_allowed_url("https://www.youtube.com/results?search_query=" + quote(query), chrome=chrome)
        return open_allowed_url("https://www.google.com/search?" + urlencode({"q": query}), chrome=chrome)


    # 'abra Chrome e YouTube' / 'abre meu navegador Chrome e abre YouTube'
    if re.search(r"\b(?:abra|abre|abrir|inicie|quero abrir)\b", value):
        chrome = "chrome" in value
        if chrome and session is not None:
            session.prefer_chrome = True
        chrome = chrome or bool(getattr(session, "prefer_chrome", False))
        if "youtube" in value:
            return open_allowed_url(SAFE_SITES["youtube"], chrome=chrome)
        if "google" in value or ("navegador" in value and chrome):
            return open_allowed_url(SAFE_SITES["google"], chrome=chrome)
        if "wikipedia" in value:
            return open_allowed_url(SAFE_SITES["wikipedia"], chrome=chrome)

    match = re.search(r"^(?:pesquise|pesquisa|pesquisar|busque|buscar|procure)\s+(.+?)"
                      r"\s+(?:na|pela|pela\s+internet\s+na)\s+wikipedia$", value)
    if match:
        return "Resultados da Wikipédia:\n" + wikipedia_lookup(match[1])
    match = re.fullmatch(r"(?:pesquise|pesquisa)\s+sobre\s+(.+)", value)
    if match:
        return "Resultados da Wikipédia:\n" + wikipedia_lookup(match[1])

    # Pedidos diretos de consulta textual, somente domínio Wikipédia.
    match = re.fullmatch(r"/pesquisar\s+(.+)", value)
    if match:
        return "Resultados da Wikipédia:\n" + wikipedia_lookup(match[1])
    return None


def public_question_to_query(message):
    """Pesquisa Wikipédia automaticamente em perguntas gerais, sem dados pessoais."""
    value = command_text(message)
    if len(value) > 160 or re.search(
            r"\b(meu|minha|meus|minhas|eu|cpf|senha|token|email|conta|familia|pai|mae)\b",
            value):
        return None
    match = re.match(
        r"^(?:o que e|quem foi|quem e|onde fica|qual a historia de|"
        r"o que significa)\s+(.+)", value
    )
    if not match:
        return None
    query = match[1].strip(" ?!.")
    # Referências como "ele" dependem da conversa; pesquisá-las na Wikipédia
    # troca o assunto e pode gerar uma resposta incorreta.
    if query in {"ele", "ela", "isso", "aquilo", "esse", "essa", "este", "esta"}:
        return None
    return query if len(query) >= 3 else None
