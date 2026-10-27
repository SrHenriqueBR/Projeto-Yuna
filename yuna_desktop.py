"""Yuna Desktop: janela profissional de chat, avatar, voz e documentos locais.

O launcher padrão inicia esta interface sem abrir console CMD. O motor de
conversa e SQLite são os mesmos da mascote e do modo terminal.
"""
import html
from pathlib import Path
from queue import Queue
import sys
from threading import Thread

from PySide6.QtCore import Qt, QTimer, Signal, QObject, QUrl
from PySide6.QtGui import QMovie, QPixmap, QTextCursor
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QFrame, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QPlainTextEdit,
    QPushButton, QScrollArea, QSplitter, QVBoxLayout, QWidget
)

from computer import Computer
from document_library import DocumentLibrary, analyze_document, check_source
from self_model import VERSION
from voice import speak_windows, synthesize_edge, speech_text
from yuna import Memory, ROOT, MODEL, ask_model, handle_message, startup_greeting


ASSETS = ROOT / "assets"
LIBRARY = DocumentLibrary(ROOT / "data")


class Composer(QPlainTextEdit):
    """Enter envia; Shift+Enter cria nova linha, sem limite fixo de caracteres."""
    submit = Signal()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not (
                event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            self.submit.emit()
            event.accept()
            return
        super().keyPressEvent(event)


class DesktopSignals(QObject):
    loaded = Signal(object)
    replied = Signal(str, bool)
    status = Signal(str)
    error = Signal(str)
    library = Signal(object)
    saved = Signal(str)
    audio_ready = Signal(str)
    audio_error = Signal(str)


class DesktopWorker(Thread):
    """Todas as ações SQLite e de modelo ficam nesta thread, fora da UI."""
    def __init__(self, signals):
        super().__init__(daemon=True)
        self.signals = signals
        self.queue = Queue()

    def submit(self, message):
        self.queue.put(("chat", message))

    def analyze(self, file_path, question):
        self.queue.put(("analyze", str(file_path), question))

    def archive(self, file_path):
        self.queue.put(("archive", str(file_path)))

    def refresh(self):
        self.queue.put(("refresh",))

    def stop(self):
        self.queue.put(None)

    def run(self):
        try:
            memory = Memory(ROOT / "data" / "yuna.db")
            computer = Computer()
            history = memory.db.execute(
                "SELECT role, content FROM messages ORDER BY id DESC LIMIT 45"
            ).fetchall()
            self.signals.loaded.emit(list(reversed(history)))
            self.signals.library.emit(LIBRARY.entries())
            self.signals.status.emit("Pronta • Ollama local")
        except Exception as exc:
            self.signals.error.emit("Não consegui iniciar o cérebro local: " + str(exc))
            return
        try:
            while True:
                task = self.queue.get()
                if task is None:
                    break
                kind = task[0]
                try:
                    if kind == "chat":
                        question = task[1].strip()
                        if not question:
                            continue
                        self.signals.status.emit("Yuna está pensando...")
                        answer = handle_message(memory, question, computer)
                        self.signals.replied.emit(answer, False)
                        self.signals.status.emit("Pronta • conversa local")
                    elif kind == "analyze":
                        source, question = task[1], task[2]
                        self.signals.status.emit("Lendo documento e analisando com Ollama...")
                        answer = analyze_document(source, ask_model, question)
                        # Nunca registrar texto do documento no histórico SQLite.
                        self.signals.replied.emit(answer, True)
                        self.signals.status.emit("Análise concluída • arquivo não guardado")
                    elif kind == "archive":
                        self.signals.status.emit("Guardando cópia com autorização...")
                        item = LIBRARY.add(task[1])
                        self.signals.library.emit(LIBRARY.entries())
                        self.signals.saved.emit(item["name"])
                        self.signals.status.emit("Documento guardado na biblioteca local")
                    elif kind == "refresh":
                        self.signals.library.emit(LIBRARY.entries())
                except Exception as exc:
                    self.signals.error.emit(str(exc))
                    self.signals.status.emit("Operação não concluída")
        finally:
            memory.close()


STYLE = """
QMainWindow { background: #11101a; }
QWidget { font-family: "Segoe UI"; font-size: 12px; color: #eae8f2; }
QFrame#sidebar { background: #191726; border-right: 1px solid #302b44; }
QFrame#header { background: #181625; border-bottom: 1px solid #302b44; }
QLabel#brand { font-size: 23px; font-weight: 700; color: #f4ecff; }
QLabel#subtle { color: #aaa3bd; }
QLabel#section { color: #b8a9ea; font-size: 12px; font-weight: 700; }
QPushButton { background: #302a45; border: 1px solid #50416a;
              border-radius: 10px; color: #f7f3ff; padding: 10px 13px; }
QPushButton:hover { background: #48395f; }
QPushButton:disabled { color: #817d8e; background: #242232; border-color: #343043; }
QPushButton#primary { background: #7956cc; border: 1px solid #a58bfc;
                      font-weight: 700; }
QPushButton#primary:hover { background: #8b67e5; }
QPushButton#ghost { background: #201d2d; border: 1px solid #373147; }
QComboBox { background: #282337; border: 1px solid #55456f;
            border-radius: 10px; padding: 9px; }
QComboBox QAbstractItemView { background: #272237; }
QPlainTextEdit { background: #242033; border: 1px solid #574371;
                 border-radius: 12px; padding: 12px; font-size: 13px; }
QPlainTextEdit:focus { border: 1px solid #9977ea; }
QListWidget { background: transparent; border: none; outline: 0; }
QListWidget::item { padding: 12px; border-radius: 8px; margin: 2px; }
QListWidget::item:selected { background: #503c78; }
QScrollArea { background: #11101a; border: none; }
QScrollBar:vertical { width: 9px; background: #191623; }
QScrollBar::handle:vertical { background: #665080; border-radius: 4px; }
"""


class YunaDesktop(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Yuna {VERSION} • Espaço pessoal")
        self.resize(1160, 765)
        self.setMinimumSize(830, 550)
        self.setStyleSheet(STYLE)
        self.pending_path = None
        self.voice_index = 0
        self.voice_busy = False
        self.audio_file = None
        self._changing_voice = False
        self._edge_consent = False
        self.microphone_busy = False

        self.signals = DesktopSignals()
        self.worker = DesktopWorker(self.signals)
        self.setup_ui()
        self.attach_events()

        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(0.85)
        self.player.mediaStatusChanged.connect(self.playback_status)
        self.player.errorOccurred.connect(self.playback_error)

        self.worker.start()

    def setup_ui(self):
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(2)
        self.setCentralWidget(splitter)

        side = QFrame()
        side.setObjectName("sidebar")
        side.setMinimumWidth(220)
        side.setMaximumWidth(335)
        sidebar = QVBoxLayout(side)
        sidebar.setContentsMargins(20, 24, 20, 20)
        sidebar.setSpacing(13)

        logo = QLabel("☾  YUNA")
        logo.setObjectName("brand")
        sidebar.addWidget(logo)

        avatar = QLabel("🖤")
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setFixedHeight(190)
        avatar.setStyleSheet(
            "background:#242036;border:1px solid #403352;"
            "border-radius:17px;font-size:50px"
        )
        # O GIF é opcional e permanece no diretório de imagens do usuário.
        self.avatar_movie = None
        for filename in ("yuna.gif", "yuna_idle.gif", "yuna_animada.gif"):
            candidate = ASSETS / filename
            if candidate.is_file():
                movie = QMovie(str(candidate))
                if movie.isValid():
                    movie.setScaledSize(__import__("PySide6.QtCore", fromlist=["QSize"]).QSize(172, 172))
                    avatar.setMovie(movie)
                    movie.start()
                    self.avatar_movie = movie
                    break
        if self.avatar_movie is None:
            for filename in ("yuna_idle.png", "yuna_wave.png"):
                candidate = ASSETS / filename
                if candidate.is_file():
                    image = QPixmap(str(candidate))
                    if not image.isNull():
                        avatar.setPixmap(image.scaled(
                            178, 178, Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation
                        ))
                        break
        sidebar.addWidget(avatar)

        self.sidebar_caption = QLabel(f"Modelo local: {MODEL}")
        self.sidebar_caption.setObjectName("subtle")
        self.sidebar_caption.setWordWrap(True)
        sidebar.addWidget(self.sidebar_caption)

        title = QLabel("SUA BIBLIOTECA")
        title.setObjectName("section")
        sidebar.addWidget(title)
        sidebar.addWidget(QLabel("Arquivos que você autorizou guardar."))

        self.files_list = QListWidget()
        self.files_list.setToolTip("Selecione um documento para analisar outra vez.")
        sidebar.addWidget(self.files_list, 1)

        self.open_attachment = QPushButton("＋  Anexar documento")
        self.open_attachment.setObjectName("primary")
        sidebar.addWidget(self.open_attachment)
        self.save_attachment = QPushButton("↧  Guardar na biblioteca")
        self.save_attachment.setEnabled(False)
        sidebar.addWidget(self.save_attachment)
        self.library_hint = QLabel("Os anexos não são guardados automaticamente.")
        self.library_hint.setObjectName("subtle")
        self.library_hint.setWordWrap(True)
        sidebar.addWidget(self.library_hint)

        center = QFrame()
        content = QVBoxLayout(center)
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(0)

        header = QFrame()
        header.setObjectName("header")
        top = QHBoxLayout(header)
        top.setContentsMargins(23, 17, 23, 17)
        heading = QVBoxLayout()
        name = QLabel("Conversa com a Yuna")
        name.setStyleSheet("font-size:19px;font-weight:700;color:#f4efff")
        heading.addWidget(name)
        self.status = QLabel("Preparando memória local...")
        self.status.setObjectName("subtle")
        heading.addWidget(self.status)
        top.addLayout(heading, 1)
        self.voice_selector = QComboBox()
        self.voice_selector.addItems(
            ["🔇 Sem voz", "🔊 Windows offline", "🔊 Edge online"]
        )
        self.voice_selector.setMinimumWidth(160)
        self.voice_selector.setToolTip("Escolha como a Yuna fala as respostas.")
        top.addWidget(self.voice_selector)
        self.microphone_button = QPushButton("🎙  Falar")
        self.microphone_button.setToolTip(
            "Ditado por microfone local, se faster-whisper e sounddevice estiverem instalados."
        )
        top.addWidget(self.microphone_button)
        content.addWidget(header)

        self.messages_scroll = QScrollArea()
        self.messages_scroll.setWidgetResizable(True)
        self.messages_container = QWidget()
        self.message_column = QVBoxLayout(self.messages_container)
        self.message_column.setContentsMargins(25, 20, 25, 18)
        self.message_column.setSpacing(12)
        self.message_column.addStretch()
        self.messages_scroll.setWidget(self.messages_container)
        content.addWidget(self.messages_scroll, 1)

        footer = QFrame()
        footer.setStyleSheet("background:#191624;border-top:1px solid #302b44")
        controls = QVBoxLayout(footer)
        controls.setContentsMargins(22, 15, 22, 17)
        controls.setSpacing(10)

        self.attachment_notice = QLabel("")
        self.attachment_notice.setStyleSheet("color:#cdbbf9;")
        self.attachment_notice.setWordWrap(True)
        self.attachment_notice.hide()
        controls.addWidget(self.attachment_notice)

        composer_row = QHBoxLayout()
        self.composer = Composer()
        self.composer.setMinimumHeight(78)
        self.composer.setMaximumHeight(175)
        self.composer.setPlaceholderText(
            "Converse naturalmente ou pergunte algo sobre o documento anexado..."
        )
        composer_row.addWidget(self.composer, 1)
        self.send_button = QPushButton("Enviar  ➤")
        self.send_button.setObjectName("primary")
        self.send_button.setMinimumHeight(51)
        composer_row.addWidget(self.send_button)
        controls.addLayout(composer_row)
        hint = QLabel(
            "Enter envia • Shift+Enter quebra linha • Documentos analisados localmente com Ollama"
        )
        hint.setObjectName("subtle")
        controls.addWidget(hint)
        content.addWidget(footer)

        splitter.addWidget(side)
        splitter.addWidget(center)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([282, 878])

    def attach_events(self):
        self.signals.loaded.connect(self.load_history)
        self.signals.replied.connect(self.show_answer)
        self.signals.status.connect(self.status.setText)
        self.signals.error.connect(self.show_error)
        self.signals.library.connect(self.update_library)
        self.signals.saved.connect(self.saved_file)
        self.signals.audio_ready.connect(self.play_audio)
        self.signals.audio_error.connect(self.voice_error)

        self.send_button.clicked.connect(self.send_message)
        self.composer.submit.connect(self.send_message)
        self.open_attachment.clicked.connect(self.select_document)
        self.save_attachment.clicked.connect(self.archive_document)
        self.files_list.itemClicked.connect(self.use_library_document)
        self.voice_selector.currentIndexChanged.connect(self.voice_changed)
        self.microphone_button.clicked.connect(self.request_microphone)
        self.setAcceptDrops(True)

    def add_message(self, author, content, *, accent=False):
        body = QFrame()
        is_user = author == "Kaizen"
        body.setMaximumWidth(760)
        border = "#7259b2" if is_user else "#36304f"
        background = "#41305d" if is_user else "#242132"
        body.setStyleSheet(
            f"QFrame {{background:{background};border:1px solid {border};"
            "border-radius:14px;}"
        )
        layout = QVBoxLayout(body)
        layout.setContentsMargins(16, 12, 16, 13)
        layout.setSpacing(5)
        role = QLabel(author)
        role.setStyleSheet(
            "color:#d9c5ff;background:transparent;border:0;"
            "font-size:11px;font-weight:700"
        )
        text = QLabel(str(content))
        text.setTextFormat(Qt.TextFormat.PlainText)
        text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        text.setWordWrap(True)
        text.setMinimumWidth(120)
        text.setStyleSheet(
            "color:#f3f0fa;background:transparent;border:0;"
            "font-size:13px;line-height:140%"
        )
        if accent:
            role.setText("Yuna • documento")
        layout.addWidget(role)
        layout.addWidget(text)
        line = QHBoxLayout()
        line.addWidget(body)
        if is_user:
            line.insertStretch(0)
        else:
            line.addStretch()
        self.message_column.insertLayout(self.message_column.count() - 1, line)
        QTimer.singleShot(
            0,
            lambda: self.messages_scroll.verticalScrollBar().setValue(
                self.messages_scroll.verticalScrollBar().maximum()
            )
        )

    def load_history(self, history):
        if history:
            for role, content in history:
                self.add_message("Kaizen" if role == "user" else "Yuna", content)
        else:
            self.add_message(
                "Yuna",
                "Opa, Kaizen! 🖤 Estou pronta. Podemos conversar, "
                "analisar um documento ou trabalhar em uma ideia juntos."
            )

    def update_library(self, rows):
        self.files_list.clear()
        for item in reversed(rows):
            view = QListWidgetItem("📄  " + item.get("name", "Documento"))
            view.setToolTip(item.get("saved_at", ""))
            view.setData(Qt.ItemDataRole.UserRole, item["id"])
            self.files_list.addItem(view)

    def set_busy(self, value):
        self.send_button.setEnabled(not value)
        self.composer.setEnabled(not value)
        self.open_attachment.setEnabled(not value)
        self.save_attachment.setEnabled(not value and self.pending_path is not None)
        if not value:
            self.composer.setFocus()

    def show_answer(self, answer, is_document):
        self.add_message("Yuna", answer, accent=is_document)
        self.set_busy(False)
        if is_document:
            self.say("Terminei de analisar o documento. O resultado está na tela.", private=True)
        elif not any(term in answer.lower() for term in ("c:\\", "chave api", "token:")):
            self.say(answer)

    def show_error(self, error):
        self.add_message("Yuna", "Não consegui concluir: " + str(error))
        self.set_busy(False)

    def send_message(self):
        content = self.composer.toPlainText().strip()
        if not content and not self.pending_path:
            return
        self.composer.clear()
        self.set_busy(True)
        if self.pending_path:
            self.add_message(
                "Kaizen", (content or "Analise este documento e destaque o mais útil.")
                + "\n[Anexo: " + self.pending_path.name + "]"
            )
            self.worker.analyze(self.pending_path, content)
        else:
            self.add_message("Kaizen", content)
            self.worker.submit(content)
