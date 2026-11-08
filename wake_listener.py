"""Escuta local opt-in por sessão. Não salva nem transmite gravações."""
from pathlib import Path
from threading import Event, Thread
import time

from companion_commands import wake_command


class WakeListener(Thread):
    def __init__(self, on_command, on_error, on_ready, paused, *, root=None,
                 on_status=lambda text: None, on_level=lambda value: None):
        super().__init__(daemon=True, name="YunaWakeLocal")
        self.on_command, self.on_error, self.on_ready = on_command, on_error, on_ready
        self.paused = paused
        self.root = root or Path(__file__).resolve().parent
        self.on_status, self.on_level = on_status, on_level
        self.stopped = Event()

    def stop(self):
        self.stopped.set()

    def run(self):
        if self.stopped.is_set():
            return
        try:
            from audio_capture import capture_phrase
            from speech_input import local_model, transcribe_audio
            local_model(self.on_status)
            last_command, last_at = None, 0.0
            while not self.stopped.is_set():
                if self.paused.is_set():
                    self.stopped.wait(.1)
                    continue
                audio = capture_phrase(
                    self.root, cancelled=self.stopped.is_set, paused=self.paused.is_set,
                    on_ready=self.on_ready, on_status=self.on_status, on_level=self.on_level,
                    continuous=True,
                )
                phrase = transcribe_audio(audio, cancelled=self.stopped.is_set, on_status=self.on_status)
                request = wake_command(phrase)
                moment = time.monotonic()
                if (request and not self.stopped.is_set() and not self.paused.is_set()
                        and (request != last_command or moment - last_at > 8)):
                    last_command, last_at = request, moment
                    self.paused.set()
                    self.on_command(request)
                elif phrase and not request:
                    self.on_status('Não ouvi o chamado. Comece com “Yuna”, seguido do pedido.')
        except InterruptedError:
            pass
        except Exception as exc:
            if not self.stopped.is_set():
                self.on_error("Escuta local indisponível: " + str(exc)[:240])
