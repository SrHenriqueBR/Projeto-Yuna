"""Visão opcional da tela ativa, somente sob comando explícito do usuário."""
import base64
from io import BytesIO
import json
import os
import urllib.error
import urllib.request


def describe_screen():
    """Envia captura temporária somente ao Ollama local; não grava nem envia à web."""
    if os.name != "nt":
        return "A leitura visual da tela está disponível somente no Windows."
    model = os.environ.get("YUNA_VISION_MODEL", "").strip()
    if not model:
        return ("Para eu analisar a tela, instale Pillow (py -3 -m pip install Pillow), "
                "baixe um modelo de visão no Ollama e configure YUNA_VISION_MODEL. "
                "Consulte o README. A captura só acontece ao digitar /tela.")
    if "cloud" in model.lower():
        return "Por segurança, a Yuna só aceita modelo de visão local."
    try:
        from PIL import ImageGrab
    except ImportError:
        return "A visão precisa do Pillow: execute py -3 -m pip install Pillow."
    try:
        image = ImageGrab.grab(all_screens=False)
        try:
            image.thumbnail((1280, 800))
            stream = BytesIO()
            image.convert("RGB").save(stream, format="JPEG", quality=77)
            encoded = base64.b64encode(stream.getvalue()).decode("ascii")
        finally:
            image.close()
        payload = {
            "model": model,
            "stream": False,
            "keep_alive": "2m",
            "messages": [{
                "role": "user",
                "content": ("Descreva em português brasileiro apenas o que estiver visível nesta "
                            "captura de tela. Seja objetiva, não invente conteúdo nem afirme ter "
                            "clicado ou controlado programas. Se houver dados privados, não os "
                            "repita desnecessariamente."),
                "images": [encoded]
            }],
        }
        request = urllib.request.Request(
            "http://127.0.0.1:11434/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(request, timeout=180) as response:
            answer = json.load(response)["message"]["content"]
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError("resposta vazia")
        return answer.strip()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return f"Modelo de visão não encontrado. Baixe primeiro: ollama pull {model}"
        return f"Falha ao analisar a tela no Ollama (HTTP {exc.code})."
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError) as exc:
        return f"Não consegui analisar a tela localmente: {exc}"
