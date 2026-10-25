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
from computer import command_text, normalize

UA = "Projeto-Yuna/0.12 (assistente pessoal; pesquisa pública por solicitação)"
SAFE_SITES = {"youtube": "https://www.youtube.com",
              "google": "https://www.google.com",
              "wikipedia": "https://pt.wikipedia.org"}


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
    query = query.strip()
    if not query or len(query) > 160:
        raise ValueError("Use uma pesquisa com 1 a 160 caracteres.")
    if re.search(r"(?i)\b(senha|password|cpf|token|chave\s+api|pix|endereco\s+pessoal)\b", query):
        return "Essa pesquisa pode incluir dados privados; não vou enviá-los à Wikipédia."
    params = urlencode({"q": query, "limit": 3})
    url = "https://pt.wikipedia.org/w/rest.php/v1/search/page?" + params
    request = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            results = json.load(response)
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        return "Não consegui consultar a Wikipédia agora. Tente uma busca no navegador."
    pages = results.get("pages", [])
    if not isinstance(pages, list) or not pages:
        return "Nenhum resultado encontrado na Wikipédia em português."
    lines = []
    for item in pages[:3]:
        title = item.get("title", "")
        desc = item.get("description", "") or ""
        excerpt = re.sub(r"<[^>]+>", "", item.get("excerpt", "") or "")
        pageurl = "https://pt.wikipedia.org/wiki/" + quote(str(item.get("key", title)).replace(" ", "_"), safe="")
        lines.append(f"{title}: {html.unescape(desc)}. {html.unescape(excerpt)[:240]}\nFonte: {pageurl}")
    return "\n\n".join(lines)


def handle_web_command(message):
    value = command_text(message)
    if re.search(r"\b(nao|nunca)\b", value) or re.match(r"^(?:como|por que|porque|se eu|o que acontece)\b", value):
        return None

    if re.fullmatch(r"(?:pausa|pause|pausar|pare|parar)\s*(?:o video|a musica|o som|a reproducao)?", value):
        return media_key("pause")
    if re.fullmatch(r"(?:continua|continue|retoma|retomar|reproduz|play)(?:\s+(?:o video|a musica|a reproducao))?", value):
        return media_key("play")
    if re.fullmatch(r"(?:proxima|proximo)(?:\s+(?:musica|faixa|video))?", value):
        return media_key("next")

    # 'abra Chrome e YouTube' / 'abre meu navegador Chrome e abre YouTube'
    if re.search(r"\b(?:abra|abre|abrir|inicie|quero abrir)\b", value):
        chrome = "chrome" in value
        if "youtube" in value:
            return open_allowed_url(SAFE_SITES["youtube"], chrome=chrome)
        if "google" in value or ("navegador" in value and chrome):
            return open_allowed_url(SAFE_SITES["google"], chrome=chrome)
        if "wikipedia" in value:
            return open_allowed_url(SAFE_SITES["wikipedia"], chrome=chrome)

    # Buscas explícitas em YouTube ou Google: o conteúdo NÃO é baixado por Yuna.
    match = re.search(r"\b(?:pesquise|pesquisa|pesquisar|procure|buscar|busque)\s+(.+?)"
                      r"\s+(?:no|na)\s+(youtube|google)\s*$", value)
    if match:
        query, engine = match[1].strip(), match[2]
        if len(query) > 160:
            return "Resuma a pesquisa em até 160 caracteres."
        if engine == "youtube":
            return open_allowed_url("https://www.youtube.com/results?search_query=" + quote(query), chrome=False)
        return open_allowed_url("https://www.google.com/search?" + urlencode({"q": query}), chrome=False)

    match = re.search(r"^(?:pesquise|pesquisa|pesquisar|busque|buscar|procure)\s+(.+?)"
                      r"\s+(?:na|pela|pela\s+internet\s+na)\s+wikipedia$", value)
    if match:
        return "Resultados da Wikipédia:\n" + wikipedia_lookup(match[1])

    # Pedidos diretos de consulta textual, somente domínio Wikipédia.
    match = re.fullmatch(r"/pesquisar\s+(.+)", value)
    if match:
        return "Resultados da Wikipédia:\n" + wikipedia_lookup(match[1])
    return None
