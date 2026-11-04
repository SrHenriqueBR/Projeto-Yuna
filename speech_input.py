"""Ditado opcional totalmente local para a Yuna Desktop.

Instalar separadamente faster-whisper e sounddevice. Captura somente quando
a pessoa clica em Falar. Não grava WAV em disco nem envia áudio à internet.
O primeiro uso pode baixar pesos públicos do modelo local.
"""


def listen_once(seconds=8, cancelled=None):
    if not 1 <= seconds <= 30:
        raise ValueError("A gravação deve durar entre 1 e 30 segundos.")
    if cancelled is not None and cancelled():
        raise InterruptedError("Ditado cancelado.")
    try:
        import numpy as np
        import sounddevice as sd
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError(
            "Microfone local opcional: instale com "
            "py -3 -m pip install -r requirements-voz.txt"
        ) from exc
    # As dependências são importadas apenas ao pressionar Falar.
    chunks = []
    remaining = int(seconds * 16000)
    with sd.InputStream(samplerate=16000, channels=1, dtype="float32", blocksize=1600) as stream:
        while remaining:
            if cancelled is not None and cancelled():
                raise InterruptedError("Ditado cancelado.")
            count = min(remaining, 1600)
            chunk, overflowed = stream.read(count)
            if overflowed:
                raise RuntimeError("A captura de áudio perdeu amostras. Tente novamente.")
            chunks.append(chunk.copy())
            remaining -= count
    recorded = np.concatenate(chunks)
    if cancelled is not None and cancelled():
        raise InterruptedError("Ditado cancelado.")
    model = WhisperModel("base", device="cpu", compute_type="int8")
    if cancelled is not None and cancelled():
        raise InterruptedError("Ditado cancelado.")
    segments, _ = model.transcribe(
        recorded.reshape(-1), language="pt", beam_size=3, vad_filter=True
    )
    words = " ".join(piece.text.strip() for piece in segments).strip()
    if not words:
        raise ValueError("Não identifiquei fala nesse intervalo. Tente novamente.")
    return words

