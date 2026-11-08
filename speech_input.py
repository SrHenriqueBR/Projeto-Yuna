"""Transcrição em português, local, sem gravações em disco ou envio de áudio."""
from pathlib import Path
from threading import Lock

_MODEL = None
_MODEL_LOCK = Lock()
_TRANSCRIBE_LOCK = Lock()


def local_model(on_status=lambda text: None):
    global _MODEL
    with _MODEL_LOCK:
        if _MODEL is None:
            on_status("Preparando reconhecimento local • no primeiro uso pode baixar o modelo Whisper base…")
            from faster_whisper import WhisperModel
            _MODEL = WhisperModel("base", device="cpu", compute_type="int8", cpu_threads=2)
    return _MODEL


def transcribe_audio(audio, *, cancelled=lambda: False, on_status=lambda text: None):
    if cancelled():
        raise InterruptedError("Ditado cancelado.")
    model = local_model(on_status)
    with _TRANSCRIBE_LOCK:
        if cancelled():
            raise InterruptedError("Ditado cancelado.")
        on_status("Entendendo sua fala no computador…")
        segments, _ = model.transcribe(
            audio, language="pt", beam_size=5, temperature=0,
            vad_filter=True, vad_parameters={"min_silence_duration_ms": 500},
            condition_on_previous_text=False, hotwords="Yuna, Kaizen",
        )
        words = []
        for piece in segments:
            if cancelled():
                raise InterruptedError("Ditado cancelado.")
            words.append(piece.text.strip())
    if cancelled():
        raise InterruptedError("Ditado cancelado.")
    return " ".join(words).strip()


def listen_once(seconds=20, cancelled=None, *, root=None,
                on_status=lambda text: None, on_level=lambda value: None):
    if not 1 <= seconds <= 30:
        raise ValueError("A gravação deve durar entre 1 e 30 segundos.")
    cancelled = cancelled or (lambda: False)
    if cancelled():
        raise InterruptedError("Ditado cancelado.")
    from audio_capture import capture_phrase
    audio = capture_phrase(root or Path(__file__).resolve().parent, seconds=seconds,
                           cancelled=cancelled, on_status=on_status, on_level=on_level)
    words = transcribe_audio(audio, cancelled=cancelled, on_status=on_status)
    if not words:
        raise ValueError("Ouvi áudio, mas não reconheci as palavras. Aproxime-se do microfone e tente novamente.")
    return words
