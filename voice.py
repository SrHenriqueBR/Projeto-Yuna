"""Voz da Yuna para Windows: offline por padrão; Edge TTS apenas por opt-in.

Windows usa uma voz feminina instalada via System.Speech/SAPI (sem rede).
Edge usa edge-tts (serviço online), com ritmo e tom um pouco mais jovens.
Nenhum texto é enviado a um provedor externo sem ativar o modo online.
"""
import asyncio
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

EDGE_VOICE = "pt-BR-FranciscaNeural"
EDGE_RATE = "+13%"
EDGE_PITCH = "+8Hz"
WINDOWS_RATE = 2


def speech_text(text, limit=520):
    """Sanitiza apresentação e limita duração sem modificar a conversa armazenada."""
    if not isinstance(text, str):
        return ""
    text = re.sub(r"\x60{3}[\s\S]*?\x60{3}", " ", text)
    text = re.sub(r"https?://\S+", "um link", text)
    text = re.sub(r"[\x60*_#\[\]]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0] + "..."
    return text


WINDOWS_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new()
Add-Type -AssemblyName System.Speech
$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
$voices = @($speaker.GetInstalledVoices() | Where-Object {
    $_.Enabled -and $_.VoiceInfo.Gender -eq 'Female'
})
$br = @($voices | Where-Object {$_.VoiceInfo.Culture.Name -eq 'pt-BR'})
if ($br.Count -eq 0) {
    throw 'Não encontrei voz feminina pt-BR instalada. Instale uma voz nas configurações do Windows ou ative Edge TTS.'
}
$speaker.SelectVoice($br[0].VoiceInfo.Name)
$speaker.Rate = 2
$speaker.Volume = 95
$text = [Console]::In.ReadToEnd()
if (-not [string]::IsNullOrWhiteSpace($text)) { $speaker.Speak($text) }
$speaker.Dispose()
"""


def speak_windows(text):
    """Bloqueante: executar em thread de trabalho, nunca no thread Qt."""
    if os.name != "nt":
        raise RuntimeError("A voz offline exige Windows.")
    clean = speech_text(text)
    if not clean:
        return
    ps = Path(os.environ.get("SystemRoot", r"C:\Windows")) / (
        "System32/WindowsPowerShell/v1.0/powershell.exe"
    )
    try:
        result = subprocess.run(
            [str(ps), "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", WINDOWS_SCRIPT],
            input=clean, text=True, capture_output=True, encoding="utf-8",
            errors="replace", timeout=90, shell=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f"Não consegui reproduzir a voz offline: {exc}") from exc
    if result.returncode:
        raise RuntimeError(result.stderr.strip()[:300] or "Voz offline indisponível.")


async def _edge_save(text, destination):
    try:
        # Importação direta da classe: evita um proxy lazy que certas combinações
        # de Python 3.15 e pacotes de terceiros não conseguem invocar.
        from edge_tts.communicate import Communicate
    except ImportError as exc:
        raise RuntimeError(
            "Para usar a voz online, instale: py -3 -m pip install edge-tts"
        ) from exc
    communicate = Communicate(
        speech_text(text), EDGE_VOICE, rate=EDGE_RATE, pitch=EDGE_PITCH
    )
    await communicate.save(str(destination))


def _stable_python_edge(text, destination):
    """Fallback por processo isolado: usa edge-tts no Python 3.13 se instalado.

    O Python do GUI não muda; somente a síntese é executada em uma versão estável.
    Envia ao Edge TTS apenas o texto que o usuário autorizou falar.
    """
    if os.name != "nt" or not shutil.which("py"):
        raise RuntimeError(
            "A voz encontrou incompatibilidade com imports lazy. "
            "No Windows, instale Python 3.13 e edge-tts para essa versão."
        )
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    # Não supor que ter o Python 3.13 signifique ter o pacote edge-tts.
    check = subprocess.run(
        ["py", "-3.13", "-c", "import edge_tts"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=15, shell=False, creationflags=flags
    )
    if check.returncode:
        raise RuntimeError(
            "A voz encontrou incompatibilidade com Python 3.15. "
            "Instale Python 3.13 e execute: py -3.13 -m pip install edge-tts. "
            "Depois reabra a Yuna; suas memórias ficam intactas."
        )
    result = subprocess.run(
        ["py", "-3.13", "-m", "edge_tts", "--voice", EDGE_VOICE,
         "--rate", EDGE_RATE, "--pitch", EDGE_PITCH, "--text", speech_text(text),
         "--write-media", str(destination)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=120, shell=False, creationflags=flags
    )
    if result.returncode:
        raise RuntimeError(
            "A voz via Python 3.13 também falhou: "
            + (result.stderr.strip()[-250:] or "verifique Edge TTS e a internet.")
        )


def synthesize_edge(text):
    """Produz MP3 temporário; o GUI reproduz pelo Qt e apaga depois."""
    if not speech_text(text):
        return None
    with tempfile.NamedTemporaryFile(prefix="yuna_voice_", suffix=".mp3", delete=False) as file:
        path = Path(file.name)
    try:
        try:
            asyncio.run(_edge_save(text, path))
        except TypeError as exc:
            if "lazy_import" not in str(exc):
                raise
            # Uma versão estável do interpretador evita a falha conhecida
            # nos imports de algumas dependências no Python 3.15.
            _stable_python_edge(text, path)
        if not path.stat().st_size:
            raise RuntimeError("O serviço de voz não retornou áudio.")
        return path
    except Exception:
        path.unlink(missing_ok=True)
        raise


# Voz Amanda Kelly - Sweet, Warm and Clear (ElevenLabs Voice Library).
# ID publicado no catálogo JSON2Video; uso depende de acesso na conta ElevenLabs.
AMANDA_VOICE_ID = "oi8rgjIfLgJRsQ6rbZh3"
AMANDA_MODEL = "eleven_multilingual_v2"
AMANDA_ENDPOINT = (
    "https://api.elevenlabs.io/v1/text-to-speech/"
    + AMANDA_VOICE_ID + "?output_format=mp3_44100_128"
)


def amanda_available():
    """Não salva credenciais em arquivos nem transmite uma chave sem autorização."""
    return bool(os.environ.get("ELEVENLABS_API_KEY", "").strip())


def synthesize_amanda(text):
    """Gera áudio da voz licenciada via API oficial, somente após opt-in no GUI.

    Toda solicitação envia o texto para a ElevenLabs e consome créditos do plano.
    Chave recebida do ambiente do processo (nunca salva em GitHub/SQLite).
    """
    clean = speech_text(text)
    if not clean:
        return None
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "Amanda Kelly requer uma chave API da ElevenLabs. "
            "Configure ELEVENLABS_API_KEY no PowerShell antes de abrir a Yuna."
        )
    request = urllib.request.Request(
        AMANDA_ENDPOINT,
        data=json.dumps({
            "text": clean, "model_id": AMANDA_MODEL,
            "voice_settings": {
                "stability": 0.45, "similarity_boost": 0.8,
                "style": 0.2, "use_speaker_boost": True,
            }
        }, ensure_ascii=False).encode("utf-8"),
        headers={
            "xi-api-key": key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = response.read(16 * 1024 * 1024 + 1)
            media_type = response.headers.get("Content-Type", "").lower()
            if len(data) > 16 * 1024 * 1024:
                raise RuntimeError("O áudio retornado pela ElevenLabs ultrapassou o limite.")
            if not data or ("audio" not in media_type and "octet-stream" not in media_type):
                raise RuntimeError("A ElevenLabs não devolveu um arquivo de áudio.")
    except urllib.error.HTTPError as exc:
        status = exc.code
        if status in (401, 403):
            detail = "Chave inválida, permissão insuficiente ou voz indisponível na sua conta."
        elif status == 402:
            detail = "Plano sem créditos suficientes para sintetizar áudio."
        elif status == 404:
            detail = "Amanda Kelly não está disponível na sua conta ElevenLabs."
        elif status == 429:
            detail = "Limite de solicitações ou créditos atingido na ElevenLabs."
        else:
            detail = "Não foi possível sintetizar a voz; confira o serviço ou a conta."
        # Não expor corpo de erro ou credencial na interface.
        raise RuntimeError(f"ElevenLabs HTTP {status}: {detail}") from None
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError("Sem conexão com a API ElevenLabs. Verifique a internet.") from None

    # Não guardar o áudio permanentemente.
    with tempfile.NamedTemporaryFile(
        prefix="yuna_amanda_", suffix=".mp3", delete=False
    ) as file:
        file.write(data)
        return Path(file.name)
