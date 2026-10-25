"""Janela-mascote 2D para Yuna. Iniciar com: py -3 yuna_overlay.py

Dependência da interface: PySide6. Sem câmera, microfone ou acesso oculto.
As ações existentes do Windows só são executadas por instruções diretas da pessoa.
"""
import os
from pathlib import Path
from queue import Queue
import sys
from threading import Thread

from PySide6.QtCore import QObject, QPoint, Qt, QUrl, QTimer, Signal
from PySide6.QtGui import QPixmap, QFont
from PySide6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QVBoxLayout, QWidget
)
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

from computer import Computer
from initiative import looks_like_command
from self_model import about_text, is_self_question
from voice import speak_windows, synthesize_edge, speech_text
from yuna import Memory, MODEL, ROOT, ask_model, declared_name, handle_message

ASSETS = ROOT / "assets"
POSES = ("idle", "wave", "happy", "thinking", "speaking", "sleepy")


class Messages(QObject):
    message = Signal(str)
    listening = Signal(bool)
    speech = Signal(str)
    voice_finished = Signal(str)
    edge_ready = Signal(str)
    warning = Signal(str)


class DialogueThread(Thread):
    """SQLite fica exclusivamente nesta thread; nenhum compartilhamento de conexão."""
    def __init__(self, output):
        super().__init__(daemon=True)
        self.output = output
        self.inputs = Queue()

    def submit(self, text):
        self.inputs.put(text)

    def stop(self):
        self.inputs.put(None)

    def run(self):
        try:
            memory = Memory(ROOT / "data" / "yuna.db")
            computer = Computer()
        except Exception as exc:
            self.output.warning.emit(f"Falha ao iniciar a Yuna: {exc}")
            return
        try:
            name = next((n for _, fact in reversed(memory.facts())
                         if (n := declared_name(fact))), "Kaizen")
            greeting = memory.initiative.startup(name)
            if greeting:
                self.output.message.emit(greeting)
                self.output.speech.emit(greeting)
            while True:
                message = self.inputs.get()
                if message is None:
                    break
                self.output.listening.emit(True)
                try:
                    # Usa a lógica do terminal, no mesmo banco e mesma thread.
                    if message == "/sobre":
                        answer = about_text(memory, MODEL)
                    elif message == "/estado":
                        answer = memory.affect.status_text()
                    elif message.startswith("/pensar "):
                        answer = memory.thinking.plan(message[8:].strip(), ask_model)
                        memory.export()
                    else:
                        if not looks_like_command(message):
                            memory.affect.observe(message)
                        answer = handle_message(memory, message, computer)
                    self.output.message.emit(answer)
                    self.output.speech.emit(answer)

                    if (not looks_like_command(message) and "?" not in message
                            and not is_self_question(message)):
                        if memory.initiative.enabled:
                            if memory.initiative.capture(message):
                                memory.export()
                            question = memory.initiative.maybe_propose(message, ask_model)
                            if question:
                                self.output.message.emit(question)
                                # Perguntas adicionais só aparecem no balão; não atropelam voz.
                        note = memory.thinking.maybe_reflect(message, ask_model)
                        if note:
                            memory.export()
                    self.output.listening.emit(False)
                except Exception as exc:
                    self.output.warning.emit(str(exc))
                    self.output.listening.emit(False)
        finally:
            memory.close()


class MascotImage(QLabel):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.drag_delta = None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumHeight(340)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_delta = event.globalPosition().toPoint() - self.window.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if (event.buttons() & Qt.MouseButton.LeftButton) and self.drag_delta is not None:
            self.window.move(event.globalPosition().toPoint() - self.drag_delta)

    def mouseReleaseEvent(self, event):
        self.drag_delta = None


class YunaOverlay(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Yuna · Escuridão")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(400, 590)
        self.signals = Messages()
        self.voice_engine = os.environ.get("YUNA_VOICE_ENGINE", "windows").strip().lower()
        if self.voice_engine not in {"windows", "edge", "off"}:
            self.voice_engine = "windows"
        # A opção edge só é ativada com consentimento nesta sessão de interface.
        if self.voice_engine == "edge":
            self.voice_engine = "windows"
        self.voice_busy = False
        self.thinking = False
        self.frame_index = 0
        self.last_expression = "idle"
        self.temp_mp3 = None
        self.pixmaps = {}
        self.setup_ui()
        self.setup_audio()
        self.connect_events()

        screen = QApplication.primaryScreen()
        if screen is not None:
            area = screen.availableGeometry()
            self.move(area.right() - self.width() - 18,
                      area.bottom() - self.height() - 18)

        self.dialogue = DialogueThread(self.signals)
        self.dialogue.start()
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.animate_pose)
        self.animation_timer.start(360)

    def setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(11, 8, 11, 5)
        root.setSpacing(7)
        top = QHBoxLayout()
        title = QLabel("☾ YUNA")
        title.setStyleSheet(
            "color:#e9d5ff;font-size:14px;font-weight:800;"
            "background:#1c1730;border:1px solid #513c6d;border-radius:12px;padding:8px"
        )
        top.addWidget(title)
        top.addStretch()
        self.voice_button = QPushButton()
        self.voice_button.setToolTip("Escolher voz: Windows offline, Edge online, sem voz")
        self.voice_button.clicked.connect(self.cycle_voice)
        top.addWidget(self.voice_button)
        close = QPushButton("×")
        close.setFixedWidth(30)
        close.clicked.connect(self.close)
        top.addWidget(close)
        root.addLayout(top)
        self.update_voice_button()

        self.bubble = QLabel("Iniciando minha memória... ✦")
        self.bubble.setWordWrap(True)
        self.bubble.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.bubble.setMinimumHeight(88)
        self.bubble.setMaximumHeight(138)
        self.bubble.setStyleSheet(
            "QLabel { background-color: rgba(28, 20, 46, 235); color: #f6efff;"
            "border:1px solid #8254b3; border-radius:18px; padding:12px;"
            "font-size:13px; }"
        )
        root.addWidget(self.bubble)

        self.image = MascotImage(self)
        root.addWidget(self.image, 1)
        for name in POSES:
            filename = ASSETS / f"yuna_{name}.png"
            if filename.exists():
                self.pixmaps[name] = QPixmap(str(filename))
        self.show_expression("wave")

        bar = QHBoxLayout()
        self.entry = QLineEdit()
        self.entry.setPlaceholderText("Fala comigo, Kaizen...")
        self.entry.setMaxLength(2000)
        self.entry.returnPressed.connect(self.send)
        self.entry.setStyleSheet(
            "QLineEdit {background:#1c1730;color:#fff;border:1px solid #8462a8;"
            "border-radius:12px;padding:11px;font-size:13px}"
        )
        bar.addWidget(self.entry, 1)
        self.send_button = QPushButton("Enviar")
        self.send_button.clicked.connect(self.send)
        bar.addWidget(self.send_button)
        root.addLayout(bar)

        self.status = QLabel("Arraste a mascote para mudar de lugar · sem câmera/microfone")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setStyleSheet("color:#bda7d8;font-size:10px")
        root.addWidget(self.status)

        for button in (self.voice_button, close, self.send_button):
            button.setStyleSheet(
                "QPushButton {background:#42275d;color:#f8f0ff;border-radius:10px;"
                "border:1px solid #765097;padding:9px;font-weight:600}"
                "QPushButton:hover {background:#5d3680}"
            )

    def setup_audio(self):
        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.player.setAudioOutput(self.audio)
        self.audio.setVolume(0.9)
        self.player.mediaStatusChanged.connect(self.media_status)
        self.player.errorOccurred.connect(self.media_error)

    def connect_events(self):
        self.signals.message.connect(self.show_message)
        self.signals.speech.connect(self.say)
        self.signals.listening.connect(self.set_thinking)
        self.signals.voice_finished.connect(self.voice_done)
        self.signals.edge_ready.connect(self.play_edge)
        self.signals.warning.connect(self.show_warning)

    def show_expression(self, expression):
        sprite = self.pixmaps.get(expression) or self.pixmaps.get("idle")
        if sprite is None or sprite.isNull():
            self.image.setText("☾\nYUNA\n✦")
            self.image.setStyleSheet(
                "font-size:39px;color:#d5aaff;"
                "background:rgba(48,29,75,100);border-radius:28px"
            )
            return
        self.image.setText("")
        self.image.setStyleSheet("background:transparent")
        self.image.setPixmap(sprite.scaled(
            350, 360, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        ))
        self.last_expression = expression

    def animate_pose(self):
        self.frame_index += 1
        if self.thinking:
            self.show_expression("thinking")
        elif self.voice_busy:
            # Animação 2D simples baseada no estado da voz; ainda não é lip-sync fonético.
            self.show_expression("speaking" if self.frame_index % 2 else "idle")
        elif self.frame_index % 13 == 0:
            self.show_expression("happy")
        else:
            self.show_expression("idle")

    def show_message(self, text):
        self.bubble.setText(text[:450] + ("…" if len(text) > 450 else ""))
        self.bubble.setToolTip(text)
        if not self.voice_busy:
            self.show_expression("happy")

    def set_thinking(self, active):
        self.thinking = bool(active)
        self.status.setText(
            "Yuna está pensando..." if active
            else "Arraste a mascote · Enter para conversar"
        )
        self.entry.setEnabled(not active)
        self.send_button.setEnabled(not active)
        if not active:
            self.entry.setFocus()

    def send(self):
        text = self.entry.text().strip()
        if not text or self.thinking:
            return
        self.entry.clear()
        self.bubble.setText("Hmm, deixa eu pensar nisso... ✦")
        self.dialogue.submit(text)
        self.set_thinking(True)

    def update_voice_button(self):
        labels = {"windows": "🔊 Offline", "edge": "🔊 Jovem", "off": "🔇 Muda"}
        self.voice_button.setText(labels[self.voice_engine])

    def cycle_voice(self):
        modes = {"windows": "edge", "edge": "off", "off": "windows"}
        selected = modes[self.voice_engine]
        if selected == "edge":
            answer = QMessageBox.question(
                self, "Voz online",
                "A voz jovem usa o serviço online do Edge TTS. O texto falado "
                "será enviado para geração de áudio pela internet. "
                "Não use este modo para informações pessoais ou confidenciais.\n\n"
                "Quer ativar a voz jovem online?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        self.voice_engine = selected
        self.update_voice_button()
        self.status.setText({
            "windows": "Voz feminina do Windows (offline), depende das vozes instaladas",
            "edge": "Voz jovem online ativada (pt-BR Francisca Neural)",
            "off": "Voz desligada: somente texto",
        }[selected])

    def say(self, text):
        if self.voice_engine == "off" or self.voice_busy or not speech_text(text):
            return
        self.voice_busy = True
        mode = self.voice_engine

        def worker():
            try:
                if mode == "windows":
                    speak_windows(text)
                    self.signals.voice_finished.emit("")
                else:
                    audio = synthesize_edge(text)
                    if audio is not None:
                        self.signals.edge_ready.emit(str(audio))
                    else:
                        self.signals.voice_finished.emit("")
            except Exception as exc:
                self.signals.voice_finished.emit(str(exc))

        Thread(target=worker, daemon=True).start()

    def play_edge(self, path):
        self.temp_mp3 = Path(path)
        self.player.setSource(QUrl.fromLocalFile(str(self.temp_mp3)))
        self.player.play()

    def media_status(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.player.stop()
            self.player.setSource(QUrl())
            self.cleanup_audio()
            self.voice_busy = False

    def media_error(self, error, message):
        self.voice_done(f"Reprodução de áudio: {message}")

    def cleanup_audio(self):
        if self.temp_mp3 is not None:
            self.temp_mp3.unlink(missing_ok=True)
            self.temp_mp3 = None

    def voice_done(self, error):
        self.voice_busy = False
        if error:
            self.status.setText(f"Voz: {error[:115]}")
        self.cleanup_audio()

    def show_warning(self, error):
        self.bubble.setText("Ops, encontrei um problema: " + error[:220])

    def closeEvent(self, event):
        self.dialogue.stop()
        self.player.stop()
        self.player.setSource(QUrl())
        self.cleanup_audio()
        super().closeEvent(event)


def main():
    if os.name != "nt":
        raise SystemExit("A mascote e a voz foram preparadas para Windows.")
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    window = YunaOverlay()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
