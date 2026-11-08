"""Captura local compartilhada: dispositivo explícito, frase inteira e nível visível."""
from collections import deque
import json
from pathlib import Path
from threading import Lock
from tempfile import NamedTemporaryFile

_MICROPHONE = Lock()


def input_devices():
    import sounddevice as sd
    apis = sd.query_hostapis()
    return [{"index": i, "name": d["name"], "hostapi": apis[d["hostapi"]]["name"]}
            for i, d in enumerate(sd.query_devices()) if d["max_input_channels"] > 0]


def save_input(root, device=None):
    """Persistir nome + API: índices PortAudio mudam ao reconectar USB."""
    value = None if device is None else {key: device[key] for key in ("name", "hostapi")}
    path = Path(root) / "data" / "microfone_yuna.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as file:
        temporary = Path(file.name)
        json.dump(value, file, ensure_ascii=False)
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def resolve_input(root, sd):
    try:
        selected = json.loads((Path(root) / "data" / "microfone_yuna.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        selected = None
    index = None
    if isinstance(selected, dict) and selected.get("name"):
        apis = sd.query_hostapis()
        matches = [i for i, d in enumerate(sd.query_devices())
                   if d["max_input_channels"] > 0 and d["name"] == selected["name"]
                   and apis[d["hostapi"]]["name"] == selected.get("hostapi")]
        if not matches:
            raise RuntimeError("O microfone escolhido está desconectado. Use Central → Permissões → Escolher microfone.")
        index = matches[0]
    try:
        info = sd.query_devices(index, "input")
        rate = int(info["default_samplerate"])
        sd.check_input_settings(device=index, channels=1, dtype="float32", samplerate=rate)
    except Exception as exc:
        raise RuntimeError("Não consegui abrir o microfone. Confira o dispositivo e a permissão de microfone "
                           "para aplicativos da área de trabalho nas configurações do Windows.") from exc
    return index, rate, info["name"]


class PhraseDetector:
    """Encerra após pausa, com pré-áudio e teto; não corta a cada quatro segundos."""
    def __init__(self, *, max_seconds=20, silence_seconds=1.2, frame_seconds=.1):
        self.frame_seconds = frame_seconds
        self.max_seconds, self.silence_seconds = max_seconds, silence_seconds
        self.pre_roll = deque(maxlen=max(1, round(.4 / frame_seconds)))
        self.noise = .0005
        self.reset()

    def reset(self):
        self.chunks = []
        self.pre_roll.clear()
        self.duration = self.silence = self.voiced = 0.0

    def feed(self, chunk, rms):
        threshold = max(.0015, min(.012, self.noise * 3))
        speaking = rms >= threshold
        if not self.chunks:
            self.pre_roll.append(chunk)
            if not speaking:
                self.noise = .95 * self.noise + .05 * min(rms, .004)
                return None
            self.chunks = list(self.pre_roll)
        else:
            self.chunks.append(chunk)
        self.duration += self.frame_seconds
        self.voiced += self.frame_seconds if speaking else 0
        self.silence = 0 if speaking else self.silence + self.frame_seconds
        if self.silence >= self.silence_seconds or self.duration >= self.max_seconds:
            phrase = self.chunks if self.voiced >= .2 else None
            self.reset()
            return phrase
        return None


def resample_audio(audio, rate):
    import numpy as np
    mono = np.asarray(audio, dtype=np.float32).reshape(-1)
    if rate == 16000:
        return mono
    size = round(len(mono) * 16000 / rate)
    return np.interp(np.arange(size) * rate / 16000, np.arange(len(mono)), mono).astype(np.float32)


def capture_phrase(root, *, seconds=20, cancelled=lambda: False, paused=None,
                   on_status=lambda text: None, on_level=lambda value: None,
                   on_ready=lambda: None, continuous=False):
    import numpy as np
    import sounddevice as sd
    if cancelled():
        raise InterruptedError("Microfone cancelado.")
    if not _MICROPHONE.acquire(timeout=3):
        raise RuntimeError("A captura anterior ainda está encerrando. Aguarde um instante e tente novamente.")
    try:
        index, rate, name = resolve_input(root, sd)
        frames = max(1, round(rate * .1))
        detector = PhraseDetector(max_seconds=seconds)
        waited = 0.0
        with sd.InputStream(device=index, samplerate=rate, channels=1, dtype="float32", blocksize=frames) as stream:
            on_ready()
            on_status("Ouvindo • " + name + " • fale agora")
            while True:
                if cancelled():
                    raise InterruptedError("Microfone cancelado.")
                chunk, overflowed = stream.read(frames)
                if paused is not None and paused():
                    detector.reset()
                    waited = 0
                    on_level(0)
                    continue
                if overflowed:
                    raise RuntimeError("O áudio perdeu amostras. Selecione outro microfone ou feche outros aplicativos de áudio.")
                rms = float(np.sqrt(np.mean(chunk * chunk)))
                on_level(min(100, round(rms * 2500)))
                phrase = detector.feed(chunk.copy(), rms)
                waited += .1
                if phrase is not None:
                    return resample_audio(np.concatenate(phrase), rate)
                if not continuous and waited >= 8 and not detector.chunks:
                    raise ValueError("Não detectei sua voz. Confira o nível, o botão mudo e o microfone escolhido na Central.")
    finally:
        _MICROPHONE.release()
        on_level(0)
