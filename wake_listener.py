"""Escuta local opt-in por sessão. Não salva nem transmite gravações."""
from threading import Event, Thread
import time

from companion_commands import wake_command


class WakeListener(Thread):
    def __init__(self, on_command, on_error, on_ready, paused):
        super().__init__(daemon=True, name="YunaWakeLocal")
        self.on_command, self.on_error, self.on_ready = on_command, on_error, on_ready
        self.paused = paused
        self.stopped = Event()

    def stop(self):
        self.stopped.set()

    def run(self):
        if self.stopped.is_set():
            return
        try:
            import numpy as np
            import sounddevice as sd
            from faster_whisper import WhisperModel
            # Uma carga por sessão; duas threads CPU, sem modelo remoto/API paga.
            model = WhisperModel("base", device="cpu", compute_type="int8", cpu_threads=2)
            if self.stopped.is_set():
                return
            self.on_ready()
            last_command, last_at = None, 0.0
            with sd.InputStream(samplerate=16000, channels=1, dtype="float32", blocksize=1600) as stream:
                while not self.stopped.is_set():
                    chunks = []
                    for _ in range(40):
                        if self.stopped.is_set():
                            return
                        chunk, overflowed = stream.read(1600)
                        if self.paused.is_set() or overflowed:
                            chunks = []
                            continue
                        chunks.append(chunk.copy())
                    if len(chunks) < 10 or self.paused.is_set():
                        continue
                    audio = np.concatenate(chunks).reshape(-1)
                    if float(np.sqrt(np.mean(audio * audio))) < .008:
                        continue
                    segments, _ = model.transcribe(audio, language="pt", beam_size=1,
                                                  vad_filter=True, condition_on_previous_text=False)
                    phrase = " ".join(segment.text.strip() for segment in segments)
                    request = wake_command(phrase)
                    moment = time.monotonic()
                    if (request and not self.stopped.is_set() and not self.paused.is_set()
                            and (request != last_command or moment - last_at > 8)):
                        last_command, last_at = request, moment
                        self.on_command(request)
        except Exception as exc:
            if not self.stopped.is_set():
                self.on_error("Escuta local indisponível: " + str(exc)[:180])
