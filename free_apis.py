"""Yuna 0.16 — hub mínimo e explícito de APIs públicas e modelos opcionais.

Ollama permanece padrão. Nenhuma consulta é disparada automaticamente,
nenhuma chave é gravada, nenhuma resposta externa é executada como código.
"""
import json
import os
import re
import urllib.error
import urllib.request
from urllib.parse import urlencode, quote
from office_agent import folded
from natural_interaction import classify_public_request

USER_AGENT = "Projeto-Yuna/0.16 (cliente educacional pessoal)"
MAX_RESPONSE = 90_000
PUBLIC_HOSTS = (
    "https://geocoding-api.open-meteo.com/",
    "https://api.open-meteo.com/",
    "https://openlibrary.org/",
    "https://brasilapi.com.br/",
)
AI_ENDPOINTS = {
    "gemini": "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent",
    "groq": "https://api.groq.com/openai/v1/chat/completions",
    "openrouter": "https://openrouter.ai/api/v1/chat/completions",
}
AI_KEYS = {
    "gemini": "GEMINI_API_KEY",
    "groq": "GROQ_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}
AI_MODELS = {
    "gemini": "gemini-2.5-flash-lite",
    "groq": "openai/gpt-oss-20b",
    "openrouter": "openrouter/free",
}
PRIVATE_WORDS = re.compile(
    r"\b(?:cpf|rg|senha|password|token|secret|cartao|extrato|pix|"
    r"minha conta|meu email|meu endereco|minha chave|minhas memorias)\b|"
    r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}", re.I
)


class RestrictedRedirect(urllib.request.HTTPRedirectHandler):
    """Um serviço nunca pode redirecionar consultas para outro host."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("O provedor tentou redirecionar para um destino inesperado.")


def _json_request(url, *, body=None, headers=None, allowed=None, timeout=12):
    allowed = allowed or PUBLIC_HOSTS
    if not any(url.startswith(prefix) for prefix in allowed):
        raise ValueError("Destino de API não autorizado.")
    method = "POST" if body is not None else "GET"
    request = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8") if body is not None else None,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json", **(headers or {})},
        method=method,
    )
    try:
        opener = urllib.request.build_opener(RestrictedRedirect)
        with opener.open(request, timeout=timeout) as response:
            raw = response.read(MAX_RESPONSE + 1)
        if len(raw) > MAX_RESPONSE:
            raise RuntimeError("Resposta maior que o limite de segurança.")
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Resposta inválida do provedor.")
        return data
    except urllib.error.HTTPError as exc:
        # Nunca mostrar payload/headers do servidor (podem conter dados sensíveis).
        if exc.code == 429:
            raise RuntimeError("Limite de uso desta API atingido. Tente novamente depois.") from exc
        raise RuntimeError(f"O serviço respondeu HTTP {exc.code}.") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError("Falha de rede ao consultar o serviço.") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError("O serviço não devolveu JSON válido.") from exc


def _public_query(text, limit=90):
    query = text.strip()
    if not 2 <= len(query) <= limit or PRIVATE_WORDS.search(query):
        raise ValueError("Use um termo público curto, sem dados pessoais ou segredos.")
    return query


def weather(city):
    city = _public_query(city, 75)
    search = _json_request(
        "https://geocoding-api.open-meteo.com/v1/search?"
        + urlencode({"name": city, "count": 1, "language": "pt", "format": "json"})
    )
    places = search.get("results", [])
    if not isinstance(places, list) or not places:
        return "Não encontrei essa cidade no Open-Meteo. Informe cidade e estado."
    place = places[0]
    lat, lon = place.get("latitude"), place.get("longitude")
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in (lat, lon)):
        raise RuntimeError("A API não retornou coordenadas válidas.")
    forecast = _json_request(
        "https://api.open-meteo.com/v1/forecast?"
        + urlencode({
            "latitude": lat, "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code",
            "timezone": "auto",
        })
    )
    current = forecast.get("current", {})
    if not isinstance(current, dict) or not isinstance(current.get("temperature_2m"), (int, float)):
        raise RuntimeError("Sem temperatura atual disponível para essa cidade.")
    def show(key, unit):
        val = current.get(key)
        return f"{val}{unit}" if isinstance(val, (int, float)) else "indisponível"
    label = ", ".join(str(place.get(k)) for k in ("name", "admin1", "country")
                      if place.get(k))
    return (
        f"Clima em {label} (Open-Meteo)\n"
        f"Temperatura: {show('temperature_2m', ' °C')}\n"
        f"Sensação térmica: {show('apparent_temperature', ' °C')}\n"
        f"Umidade relativa: {show('relative_humidity_2m', '%')}\n"
        f"Horário da medição: {current.get('time', 'não informado')}\n"
        "Fonte: https://open-meteo.com/"
    )


def books(query):
    query = _public_query(query, 100)
    data = _json_request(
        "https://openlibrary.org/search.json?"
        + urlencode({"q": query, "limit": 5,
                     "fields": "key,title,author_name,first_publish_year"})
    )
    records = data.get("docs", [])
    if not isinstance(records, list) or not records:
        return "Nenhum livro encontrado na Open Library."
    lines = ["Livros encontrados na Open Library:"]
    for i, book in enumerate(records[:5], 1):
        if not isinstance(book, dict):
            continue
        name = str(book.get("title") or "Sem título")[:160]
        authors = book.get("author_name")
        author = ", ".join(str(x) for x in authors[:2]) if isinstance(authors, list) else "Autor não informado"
        year = book.get("first_publish_year", "ano não informado")
        key = str(book.get("key") or "")
        link = "https://openlibrary.org" + key if re.fullmatch(r"/works/OL\d+W", key) else "https://openlibrary.org"
        lines.append(f"{i}. {name} — {author} ({year})\n{link}")
    return "\n".join(lines)


def cep_lookup(value):
    digits = re.sub(r"[-.\s]", "", value)
    if not re.fullmatch(r"\d{8}", digits):
        raise ValueError("Informe um CEP com oito números, por exemplo 01310930.")
    info = _json_request("https://brasilapi.com.br/api/cep/v2/" + digits)
    if not isinstance(info.get("city"), str):
        raise RuntimeError("A BrasilAPI não retornou um endereço válido.")
    return (
        f"Consulta explícita de CEP {digits} (BrasilAPI)\n"
        f"Cidade: {info.get('city', 'indisponível')}\n"
        f"Estado: {info.get('state', 'indisponível')}\n"
        f"Bairro: {info.get('neighborhood') or 'não informado'}\n"
        f"Logradouro: {info.get('street') or 'não informado'}\n"
        "Atenção: o CEP foi enviado à BrasilAPI, e o resultado pode precisar de confirmação.\n"
        "Fonte: https://brasilapi.com.br/docs"
    )


def ai_providers_status():
    lines = [
        "Provedores de IA opcionais (Ollama permanece padrão):",
        "Sem chamada automática, sem encaminhar memória, arquivos, tela ou histórico.",
    ]
    for name, env in AI_KEYS.items():
        status = "chave configurada" if os.environ.get(env, "").strip() else "sem chave"
        lines.append(f"- {name}: {status}; modelo fixo {AI_MODELS[name]}")
    lines.append("Basta dizer: 'Yuna, pergunte ao Gemini o que é Python'.")
    lines.append("Cotas gratuitas e cobrança dependem do plano de cada provedor.")
    return "\n".join(lines)


def ask_external_ai(provider, question):
    """Só /ia explícito. Respostas nunca tornam ações operacionais."""
    if provider not in AI_ENDPOINTS:
        raise ValueError("Provedor não suportado; use gemini, groq ou openrouter.")
    question = _public_query(question, 500)
    key_name = AI_KEYS[provider]
    token = os.environ.get(key_name, "").strip()
    if not token:
        return (
            f"A chave {key_name} não está configurada. "
            f"Ative uma chave do {provider} se desejar usar esse provedor. "
            "O Ollama continua funcionando gratuitamente sem ela."
        )
    url = AI_ENDPOINTS[provider]
    instructions = (
        "Responda em português brasileiro, com clareza e sem inventar fatos. "
        "Você responde uma pergunta técnica pública. Não alegue acesso ao "
        "computador, aos arquivos ou às memórias do usuário."
    )
    if provider == "gemini":
        request_body = {
            "contents": [{"role": "user", "parts": [{"text": instructions + "\n\n" + question}]}],
            "generationConfig": {"maxOutputTokens": 400},
        }
        headers = {"Content-Type": "application/json", "x-goog-api-key": token}
    else:
        request_body = {
            "model": AI_MODELS[provider],
            "messages": [{"role": "system", "content": instructions},
                         {"role": "user", "content": question}],
            "max_tokens": 400,
        }
        headers = {"Content-Type": "application/json", "Authorization": "Bearer " + token}
    response = _json_request(
        url, body=request_body, headers=headers,
        allowed=(url,), timeout=35
    )
    if provider == "gemini":
        candidates = response.get("candidates", [])
        parts = (candidates[0].get("content", {}).get("parts", [])
                 if isinstance(candidates, list) and candidates else [])
        texts = [p.get("text") for p in parts if isinstance(p, dict) and isinstance(p.get("text"), str)]
        answer = "\n".join(texts)
    else:
        choices = response.get("choices", [])
        answer = (choices[0].get("message", {}).get("content", "")
                  if isinstance(choices, list) and choices else "")
    if not isinstance(answer, str) or not answer.strip():
        raise RuntimeError("O provedor não retornou uma resposta de texto.")
    return (
        f"Resposta externa do {provider} ({AI_MODELS[provider]}):\n"
        + answer.strip()[:2800]
        + "\nConsulta explícita. As informações podem conter erros."
    )


def hub_help():
    return (
        "Eu consigo pesquisar sem você decorar comandos, Kaizen! 🖤\n\n"
        "Experimente conversar assim:\n"
        "• Yuna, como está o tempo em Uberlândia?\n"
        "• Procure livros sobre inteligência artificial.\n"
        "• Consulte o CEP 01310930.\n"
        "• Pergunte ao Gemini o que é programação funcional.\n"
        "• Pergunte ao Groq como organizar código Python.\n"
        "• Pergunte ao OpenRouter o que são redes neurais.\n\n"
        "Clima usa o Open-Meteo; livros usam a Open Library; CEP usa a BrasilAPI. "
        "Gemini, Groq e OpenRouter são opcionais e exigem chaves próprias. "
        "Não consulto modelos online sem seu pedido nem envio minhas memórias."
    )


def handle_hub(message):
    """Roteador sem LLM; evita acionamentos por negação ou frases hipotéticas."""
    message = str(message).strip()
    low = folded(message)
    if low in ("/apis", "/api", "/integracoes"):
        return hub_help()
    if low in ("/ias", "/provedores"):
        return ai_providers_status()
    if low.startswith("/clima "):
        return weather(message[7:])
    if low.startswith("/livros "):
        return books(message[8:])
    if low.startswith("/cep "):
        return cep_lookup(message[5:])
    match = re.fullmatch(r"/ia\s+(gemini|groq|openrouter)\s+(.+)", message, flags=re.I | re.S)
    if match:
        return ask_external_ai(match[1].lower(), match[2])
    intent = classify_public_request(message)
    if intent is not None:
        if intent.operation == "weather":
            return weather(intent.argument)
        if intent.operation == "books":
            return books(intent.argument)
        if intent.operation == "cep":
            return cep_lookup(intent.argument)
        if intent.operation == "external_ai":
            return ask_external_ai(intent.provider, intent.argument)

    # Compatibilidade com pedidos antigos, sem exigir comandos visíveis.
    natural = re.sub(r"^(?:ei|oi|ola|opa)\s+", "", low)
    natural = re.sub(r"^yuna[, ]+", "", natural)
    w = re.fullmatch(r"(?:qual (?:e|esta) o )?clima (?:em|de|para) ([a-z0-9À-ÿ ,.-]{2,75})\??", natural)
    if w:
        return weather(w[1])
    b = re.fullmatch(r"(?:pesquise|busque|procure) livros (?:sobre|de) (.{2,100})", natural)
    if b:
        return books(b[1])
    return None
