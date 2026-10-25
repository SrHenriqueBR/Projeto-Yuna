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
    QApplication, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QVBoxLayout, QWidget
)
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

from computer import Computer
from initiative import looks_like_command
from self_model import about_text, is_self_question
from voice import speak_windows, synthesize_edge, synthesize_amanda, amanda_available, speech_text
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
        if self.voice_engine not in {"windows", "edge", "amanda", "off"}:
            self.voice_engine = "windows"
        # A opção edge só é ativada com consentimento nesta sessão de interface.
        if self.voice_engine in {"edge", "amanda"}:
            self.voice_engine = "windows"
        self.voice_busy = False
        self.voice_confirm_pending = False
        self.voice_confirm_target = None
        self.latest_message = ''
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
        self.voice_button.setToolTip("Alternar voz: Windows offline, Edge online, sem voz")
        self.voice_button.clicked.connect(self.cycle_voice)
        top.addWidget(self.voice_button)
        self.amanda_button = QPushButton("🎙 Amanda")
        self.amanda_button.setToolTip("Ativar Amanda Kelly (ElevenLabs, requer chave API)")
        self.amanda_button.clicked.connect(self.select_amanda)
        top.addWidget(self.amanda_button)
        # Confirmação dentro da mascote: evita que janelas modais fechem um Qt.Tool.
        self.cancel_voice_button = QPushButton("Cancelar")
        self.cancel_voice_button.clicked.connect(self.cancel_voice_consent)
        self.cancel_voice_button.hide()
        top.addWidget(self.cancel_voice_button)
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

        for button in (self.voice_button, self.amanda_button, self.cancel_voice_button, close, self.send_button):
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
        self.latest_message = text
        # Nunca sobrescrever o aviso de privacidade enquanto a confirmação está pendente.
        if self.voice_confirm_pending:
            return
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
        labels = {"windows": "🔊 Offline", "edge": "🔊 Jovem",
                  "amanda": "🎙 Amanda", "off": "🔇 Muda"}
        self.voice_button.setText(labels[self.voice_engine])

    def cancel_voice_consent(self):
        if not self.voice_confirm_pending:
            return
        self.voice_confirm_pending = False
        self.voice_confirm_target = None
        self.cancel_voice_button.hide()
        self.amanda_button.show()
        self.update_voice_button()
        self.bubble.setText(
            self.latest_message[:450] if self.latest_message
            else "Beleza! A voz anterior continua selecionada. 🖤"
        )
        self.status.setText("Voz anterior mantida. Nenhum texto novo foi enviado à API.")

    def request_voice_consent(self, selected):
        if selected == "amanda" and not amanda_available():
            self.status.setText("Amanda Kelly precisa da chave ELEVENLABS_API_KEY.")
            self.bubble.setText(
                "Quero usar a Amanda Kelly também! Mas falta configurar a chave da "
                "ElevenLabs antes de abrir a Yuna. "
                "No PowerShell, use: $env:ELEVENLABS_API_KEY = Read-Host "
                "'Cole sua chave API'; depois execute py -3 yuna_overlay.py. "
                "A chave nunca deve ser enviada para o chat ou colocada no GitHub."
            )
            return
        self.voice_confirm_pending = True
        self.voice_confirm_target = selected
        self.voice_button.setText("✓ Confirmar")
        self.amanda_button.hide()
        self.cancel_voice_button.show()
        self.bubble.setToolTip("")
        if selected == "amanda":
            warning = (
                "Usar Amanda Kelly? A voz é da ElevenLabs (online) e envia o "
                "TEXTO FALADO para a API, consumindo créditos. "
                "Sua conta precisa ter acesso à voz. "
                "Não envie informações privadas ou confidenciais. "
                "Clique em Confirmar ou Cancelar."
            )
        else:
            warning = (
                "Ativar voz Jovem? Ela usa Edge TTS pela internet e ENVIA O TEXTO "
                "FALADO para gerar áudio. Não a utilize para assuntos confidenciais. "
                "Clique em Confirmar ou Cancelar."
            )
        self.bubble.setText(warning)
        self.status.setText("Aguardando sua autorização · a nova voz ainda está DESLIGADA")

    def select_amanda(self):
        if self.voice_confirm_pending:
            return
        if self.voice_engine == "amanda":
            self.status.setText("Amanda Kelly já está selecionada.")
            return
        self.request_voice_consent("amanda")

    def cycle_voice(self):
        if self.voice_confirm_pending:
            target = self.voice_confirm_target
            if target not in {"edge", "amanda"}:
                return
            if target == "amanda" and not amanda_available():
                self.cancel_voice_consent()
                self.status.setText("Ainda falta ELEVENLABS_API_KEY para usar Amanda Kelly.")
                return
            self.voice_confirm_pending = False
            self.voice_confirm_target = None
            self.cancel_voice_button.hide()
            self.amanda_button.show()
            self.voice_engine = target
            self.update_voice_button()
            self.bubble.setText(
                "Pff, agora sim! Testando a minha voz nova... ✦"
            )
            self.status.setText(
                "Amanda Kelly online ativada · créditos ElevenLabs"
                if target == "amanda" else
                "Voz jovem online ativada · texto falado enviado ao Edge TTS"
            )
            # Frase fixa, nunca envia histórico de conversa no teste.
            if self.voice_busy:
                self.status.setText(
                    "Voz ativada. Envie uma mensagem quando a fala anterior terminar."
                )
            else:
                self.say("E aí, Kaizen! Agora eu tenho voz. Hahaha! Gostou?")
            self.raise_()
            self.activateWindow()
            return

        # A voz Amanda tem botão dedicado. Preservar ciclo antigo simples.
        selected = {"windows": "edge", "edge": "off",
                    "amanda": "off", "off": "windows"}[self.voice_engine]
        if selected == "edge":
            self.request_voice_consent("edge")
            return
        self.voice_engine = selected
        self.update_voice_button()
        self.status.setText({
            "windows": "Voz feminina do Windows (offline), depende das vozes instaladas",
            "edge": "Voz jovem online ativada (pt-BR Francisca Neural)",
            "amanda": "Amanda Kelly online ativada (ElevenLabs, consome créditos)",
            "off": "Voz desligada: somente texto",
        }[selected])

    def say(self, text):
        if self.voice_engine == "off" or self.voice_busy or not speech_text(text):
            return
        self.voice_busy = True
        mode = self.voice_engine
        self.status.setText("Preparando voz...")

        def worker():
            try:
                if mode == "windows":
                    speak_windows(text)
                    self.signals.voice_finished.emit("")
                    return
                if mode == "edge":
                    audio = synthesize_edge(text)
                elif mode == "amanda":
                    audio = synthesize_amanda(text)
                else:
                    self.signals.voice_finished.emit("Motor de voz desconhecido.")
                    return
                # IMPORTANTE: fora do 'else'. Nas versões anteriores, este
                # bloco era inalcançável e nenhum MP3 chegava ao QMediaPlayer.
                if audio is not None:
                    self.signals.edge_ready.emit(str(audio))
                else:
                    self.signals.voice_finished.emit("")
            except Exception as exc:
                self.signals.voice_finished.emit(str(exc))

        Thread(target=worker, daemon=True).start()

    def play_edge(self, path):
        """Recebe o MP3 na thread de UI, reproduz e informa o que está acontecendo."""
        audio = Path(path)
        if not audio.is_file() or audio.stat().st_size == 0:
            self.voice_done("Áudio não foi gerado. Verifique o motor de voz.")
            return
        self.temp_mp3 = audio
        self.status.setText("Reproduzindo voz...")
        self.player.setSource(QUrl.fromLocalFile(str(audio)))
        self.player.play()

    def media_status(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.player.stop()
            self.player.setSource(QUrl())
            self.cleanup_audio()
            self.voice_busy = False
            self.status.setText("Voz reproduzida · escreva para conversar")

    def media_error(self, error, message):
        self.player.stop()
        self.player.setSource(QUrl())
        self.voice_done(
            f"Falha ao tocar MP3: {message or 'verifique a saída de áudio do Windows.'}"
        )

    def cleanup_audio(self):
        if self.temp_mp3 is not None:
            try:
                self.temp_mp3.unlink(missing_ok=True)
            except OSError:
                pass  # O player pode estar finalizando acesso ao arquivo no Windows.
            self.temp_mp3 = None

    def voice_done(self, error):
        self.voice_busy = False
        if error:
            self.status.setText(f"Erro na voz: {error[:170]}")
            self.bubble.setToolTip(f"Erro na voz: {error}")
        else:
            self.status.setText("Voz offline concluída")
        self.cleanup_audio()

    def show_warning(self, error):
        self.bubble.setText("Ops, encontrei um problema: " + error[:220])

    def closeEvent(self, event):
        self.dialogue.stop()
        self.player.stop()
        self.player.setSource(QUrl())
        self.cleanup_audio()
        super().closeEvent(event)
        # O widget é Qt.Tool, portanto não depende da contagem de janelas normais.
        QTimer.singleShot(0, QApplication.quit)


def main():
    if os.name != "nt":
        raise SystemExit("A mascote e a voz foram preparadas para Windows.")
    app = QApplication(sys.argv)
    # Uma caixa de diálogo pode ser a última janela normal enquanto o mascote
    # é Qt.Tool; não deixar o encerramento implícito fechar a Yuna.
    app.setQuitOnLastWindowClosed(False)
    app.setFont(QFont("Segoe UI", 10))
    window = YunaOverlay()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
