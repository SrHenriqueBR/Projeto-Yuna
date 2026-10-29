"""Yuna Desktop: janela profissional de chat, avatar, voz e documentos locais.

O launcher padrão inicia esta interface sem abrir console CMD. O motor de
conversa e SQLite são os mesmos da mascote e do modo terminal.
"""
import html
import socket
from pathlib import Path
from queue import Queue
import sys
from threading import Thread

from PySide6.QtCore import Qt, QTimer, Signal, QObject, QUrl
from PySide6.QtGui import QMovie, QPixmap, QTextCursor, QShortcut, QKeySequence, QDesktopServices
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QFrame, QHBoxLayout, QLabel, QInputDialog,
    QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QPlainTextEdit,
    QPushButton, QScrollArea, QSplitter, QVBoxLayout, QWidget
)

from computer import Computer
from document_library import DocumentLibrary, analyze_document, check_source
from avatar_state import parse_avatar_request, load_style
from yuna_avatar import YunaAvatar
from self_model import VERSION
from voice import synthesize_windows, synthesize_edge, speech_text, wave_envelope, mouth_level_at
from avatar_controller import AvatarController
from avatar3d_bridge import Avatar3DBridge
from battery_life import BatteryCompanion, read_battery, public_battery
from avatar_reactions import reaction_for_text
from action_diagnostics import diagnose_failure
from persona_commands import parse_voice_preference
from persona_store import load_preferences, save_preferences
from emergency_stop import is_stop_request
from game_sessions import GameSession
from camera_watch import CameraPermission, parse_camera_source
from camera_commands import is_camera_view_request
from remote_camera_invite import (
    is_magi_camera_request, new_remote_camera_invite,
    validate_remote_camera_invite,
)
from camera_viewer import CameraViewer
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
    mic_ready = Signal(str)
    mic_error = Signal(str)


class DesktopWorker(Thread):
    """Todas as ações SQLite e de modelo ficam nesta thread, fora da UI."""
    def __init__(self, signals):
        super().__init__(daemon=True)
        self.signals = signals
        self.queue = Queue()
        self._cancelled = False

    def submit(self, message):
        self._cancelled = False
        self.queue.put(("chat", message))

    def cancel_pending(self):
        """Descarta respostas futuras e tarefas pendentes; não mata ações em curso."""
        self._cancelled = True
        with self.queue.mutex:
            self.queue.queue.clear()

    def analyze(self, file_path, question):
        self.queue.put(("analyze", str(file_path), question))

    def archive(self, file_path, notes=""):
        self.queue.put(("archive", str(file_path), str(notes)[:3000]))

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
                        if not self._cancelled:
                            self.signals.replied.emit(answer, False)
                        self.signals.status.emit("Pronta • conversa local")
                    elif kind == "analyze":
                        source, question = task[1], task[2]
                        self.signals.status.emit("Lendo documento e analisando com Ollama...")
                        answer = analyze_document(source, ask_model, question)
                        # Nunca registrar texto do documento no histórico SQLite.
                        if not self._cancelled:
                            self.signals.replied.emit(answer, True)
                        self.signals.status.emit("Análise concluída • arquivo não guardado")
                    elif kind == "archive":
                        self.signals.status.emit("Guardando cópia com autorização...")
                        item = LIBRARY.add(task[1], task[2])
                        self.signals.library.emit(LIBRARY.entries())
                        self.signals.saved.emit(item["name"])
                        self.signals.status.emit("Documento guardado na biblioteca local")
                    elif kind == "refresh":
                        self.signals.library.emit(LIBRARY.entries())
                except Exception as exc:
                    self.signals.error.emit(diagnose_failure(exc).message())
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
        self.avatar_window = None
        self.avatar_controller = AvatarController()
        self.avatar_bridge = None  # opt-in: zero portas abertas sem ação do usuário
        self._avatar_event_sequence = 0
        self._speech_generation = 0
        self._active_speech_id = None
        self.last_avatar_request = None
        self.from_library = False
        self.last_analysis_path = None
        self.last_analysis = ""
        # Fala offline por padrão; nunca ativa serviços online sem consentimento.
        self.voice_index = 1
        self.persona = load_preferences(ROOT)
        self.voice_busy = False
        self.audio_file = None
        self._audio_levels = []
        self._changing_voice = False
        self._edge_consent = False
        self.microphone_busy = False
        self._battery_companion = BatteryCompanion()
        self._battery_mood = self._battery_companion.observe(None)

        self.signals = DesktopSignals()
        self.worker = DesktopWorker(self.signals)
        self._stop_requested = False
        self.game_session = GameSession()  # desabilitado por padrão; sem controle de jogos
        self.camera_viewer = None  # a câmera nunca é aberta automaticamente
        self.setup_ui()
        self.attach_events()

        self.stop_shortcut = QShortcut(QKeySequence("Ctrl+Shift+X"), self)
        self.stop_shortcut.activated.connect(self.emergency_stop)
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(0.85)
        self.player.mediaStatusChanged.connect(self.playback_status)
        self.player.playbackStateChanged.connect(self.playback_state_changed)
        self.player.positionChanged.connect(self.playback_position)
        self.player.errorOccurred.connect(self.playback_error)

        self.worker.start()
        # Leitura local a cada 90 s; não inicia processos nem manipula energia.
        self.battery_timer = QTimer(self)
        self.battery_timer.setInterval(90000)
        self.battery_timer.timeout.connect(self.poll_battery)
        self.battery_timer.start()
        QTimer.singleShot(2000, self.poll_battery)

    def poll_battery(self):
        """Informa bateria real sem emitir voz automaticamente."""
        status = read_battery()
        mood = self._battery_companion.observe(status)
        self._battery_mood = mood
        if self.avatar_window is not None:
            self.avatar_window.set_battery_status(status)
        if self.avatar_bridge is not None:
            self.avatar_bridge.publish(
                self.avatar_controller.snapshot,
                has_amplitude=bool(self._audio_levels),
                battery=public_battery(mood),
            )
        if mood.announcement:
            self.add_message("Yuna", mood.announcement)

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

        self.avatar_button = QPushButton("✦  Mostrar Yuna viva")
        self.avatar_button.setObjectName("primary")
        self.avatar_button.setToolTip(
            "Abre uma personagem chibi interativa que passeia na área de trabalho."
        )
        sidebar.addWidget(self.avatar_button)
        self.avatar3d_button = QPushButton("◇  Conectar Yuna 3D")
        self.avatar3d_button.setObjectName("ghost")
        self.avatar3d_button.setToolTip(
            "Conecta o avatar VRM do navegador à voz da Yuna, somente em 127.0.0.1.")
        sidebar.addWidget(self.avatar3d_button)
        self.camera_button = QPushButton("◉  Ver câmera autorizada")
        self.camera_button.setObjectName("ghost")
        self.camera_button.setToolTip(
            "Visualização opcional de webcam ou câmera RTSP da sua rede local. "
            "Sem gravação nem análise automática."
        )
        sidebar.addWidget(self.camera_button)
        self.remote_camera_button = QPushButton("◈  Magi1020 • Vídeo remoto")
        self.remote_camera_button.setObjectName("ghost")
        self.remote_camera_button.setToolTip(
            "Cria ou abre convite de videochamada voluntária no navegador. "
            "Não ativa webcams remotamente e usa serviço externo."
        )
        sidebar.addWidget(self.remote_camera_button)

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
        self.voice_selector.setCurrentIndex(1)
        top.addWidget(self.voice_selector)
        self.presentation_selector = QComboBox()
        self.presentation_selector.addItems(["♀ Feminina", "♂ Masculina", "◇ Neutra"])
        self.presentation_selector.setToolTip(
            "Como a voz deve soar; não identifica a pessoa pelo microfone.")
        self.presentation_selector.setCurrentIndex(
            {"feminina": 0, "masculina": 1, "neutra": 2}[self.persona.presentation])
        top.addWidget(self.presentation_selector)
        self.voice_test = QPushButton("▶ Testar voz")
        self.voice_test.setToolTip("Escute um teste e confira a boca da personagem.")
        top.addWidget(self.voice_test)
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
        attachment_row = QHBoxLayout()
        attachment_row.addWidget(self.attachment_notice, 1)
        self.remove_attachment = QPushButton("✕ Remover anexo")
        self.remove_attachment.setObjectName("ghost")
        self.remove_attachment.hide()
        attachment_row.addWidget(self.remove_attachment)
        controls.addLayout(attachment_row)

        composer_row = QHBoxLayout()
        self.composer = Composer()
        self.composer.setMinimumHeight(78)
        self.composer.setMaximumHeight(175)
        self.composer.setPlaceholderText(
            "Converse naturalmente ou pergunte algo sobre o documento anexado..."
        )
        composer_row.addWidget(self.composer, 1)
        self.stop_button = QPushButton("■ Parar")
        self.stop_button.setToolTip("Interromper voz e descartar tarefas pendentes (Ctrl+Shift+X)")
        self.stop_button.clicked.connect(self.emergency_stop)
        composer_row.addWidget(self.stop_button)
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
        self.signals.mic_ready.connect(self.microphone_ready)
        self.signals.mic_error.connect(self.microphone_error)

        self.avatar_button.clicked.connect(self.toggle_avatar)
        self.avatar3d_button.clicked.connect(self.toggle_avatar3d_bridge)
        self.camera_button.clicked.connect(self.open_camera_viewer)
        self.remote_camera_button.clicked.connect(self.open_remote_camera_invitation)
        self.send_button.clicked.connect(self.send_message)
        self.composer.submit.connect(self.send_message)
        self.open_attachment.clicked.connect(self.select_document)
        self.remove_attachment.clicked.connect(self.clear_attachment)
        self.save_attachment.clicked.connect(self.archive_document)
        self.files_list.itemClicked.connect(self.use_library_document)
        self.voice_selector.currentIndexChanged.connect(self.voice_changed)
        self.presentation_selector.currentIndexChanged.connect(self.presentation_changed)
        self.voice_test.clicked.connect(self.test_voice)
        self.microphone_button.clicked.connect(self.request_microphone)
        self.setAcceptDrops(True)

    def add_message(self, author, content, *, accent=False):
        body = QFrame()
        is_user = author in ("Kaizen", "Você")
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
                self.add_message("Você" if role == "user" else "Yuna", content)
        else:
            self.add_message(
                "Yuna",
                "Olá! 🖤 Estou pronta. Podemos conversar, "
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
        self.save_attachment.setEnabled(
            not value and self.pending_path is not None and not self.from_library
        )
        if not value:
            self.composer.setFocus()

    def show_answer(self, answer, is_document):
        self.add_message("Yuna", answer, accent=is_document)
        if not is_document and (self.avatar_window is not None or self.avatar_bridge is not None):
            if self.avatar_window is not None:
                self.avatar_window.reload_appearance()
            request = self.last_avatar_request
            if request is not None:
                if request[0] == "pose":
                    pose = request[1]
                    if pose in ("sit", "stand", "angry", "happy", "walk", "stop",
                                "wave", "pose", "surprised", "curious", "wink", "laugh",
                                "shy", "sleepy", "wake"):
                        chosen_pose = {
                            "stand": "idle", "stop": "idle", "wake": "idle"
                        }.get(pose, pose)
                        seconds = {
                            "sit": 20, "sleepy": 20, "shy": 7, "wink": 4,
                            "laugh": 5,
                        }.get(pose, 5)
                        phrases = {
                            "wave": "Oieee! 👋", "pose": "Ta-dã! ✨",
                            "wink": "Hihi! 😉", "laugh": "Hahaha! 🖤",
                            "shy": "E-ei! ✨", "sleepy": "Zzz...",
                            "wake": "Acordei! 🖤",
                        }
                        self._avatar_event("avatar.pose", pose=chosen_pose)
                        if self.avatar_window is not None:
                            self.avatar_window.set_pose(
                                chosen_pose, seconds, phrases.get(pose, "")
                            )
                else:
                    self._avatar_event("avatar.pose", pose="happy")
                    self._avatar_event("avatar.emotion", emotion="happy",
                                       intensity=0.8)
                    if self.avatar_window is not None:
                        self.avatar_window.set_pose(
                            "happy", 3, "Visual atualizado! 🖤"
                        )
            elif not is_document:
                # Gesto leve e opcional, só quando não há comando explícito.
                reaction = reaction_for_text(answer)
                if reaction is not None:
                    pose, emotion = reaction
                    self._avatar_event("avatar.pose", pose=pose)
                    self._avatar_event("avatar.emotion", emotion=emotion, intensity=0.65)
                    if self.avatar_window is not None:
                        self.avatar_window.set_pose(pose, 3.5)
            # A personagem só anima a boca quando a reprodução começa de verdade.
            # Não simular "talk" se a voz estiver desativada ou falhar.
        if not is_document:
            self.last_avatar_request = None
        if is_document:
            self.last_analysis_path = self.pending_path
            self.last_analysis = answer
        self.set_busy(False)
        if is_document:
            self.say("Terminei de analisar o documento. O resultado está na tela.", private=True)
        elif not any(term in answer.lower() for term in ("c:\\", "chave api", "token:")):
            self.say(answer)

    def show_error(self, error):
        self.add_message("Yuna", "Não consegui concluir: " + str(error))
        self.set_busy(False)

    def toggle_avatar(self):
        if self.avatar_window is None:
            self.avatar_window = YunaAvatar(ROOT)
        if self.avatar_window.isVisible():
            self.avatar_window.hide()
            self.avatar_button.setText("✦  Mostrar Yuna viva")
        else:
            self.avatar_window.reload_appearance()
            self.avatar_window.show()
            self.avatar_window.raise_()
            self.avatar_button.setText("✦  Esconder avatar")

    def toggle_avatar3d_bridge(self):
        """Vincula uma prévia Three.js já instalada; nenhum npm é executado."""
        if self.avatar_bridge is not None:
            self.avatar_bridge.stop()
            self.avatar_bridge = None
            self.avatar3d_button.setText("◇  Conectar Yuna 3D")
            self.status.setText("Ponte 3D desligada • avatar 2D continua disponível")
            return
        try:
            with socket.create_connection(("127.0.0.1", 5173), timeout=0.5):
                pass
        except OSError:
            QMessageBox.information(
                self, "Yuna 3D não iniciada",
                "Primeiro execute iniciar_yuna_3d.bat após instalar as dependências "
                "Node em avatar3d. Depois clique aqui para vincular a voz ao 3D. "
                "O avatar 2D continua disponível sem Node.js."
            )
            return
        bridge = None
        try:
            bridge = Avatar3DBridge().start()
            bridge.publish(self.avatar_controller.snapshot,
                           has_amplitude=bool(self._audio_levels),
                           appearance=load_style(ROOT),
                           battery=public_battery(self._battery_mood))
            opened = QDesktopServices.openUrl(QUrl(bridge.viewer_url()))
            if not opened:
                raise RuntimeError("O navegador não abriu o renderizador local.")
        except (OSError, RuntimeError) as exc:
            if bridge is not None:
                bridge.stop()
            self.status.setText("Não consegui conectar o 3D: " + str(exc)[:120])
            return
        self.avatar_bridge = bridge
        self.avatar3d_button.setText("■  Desconectar Yuna 3D")
        self.status.setText("Yuna 3D vinculada • somente estados de animação locais")

    def open_camera_viewer(self):
        """Abre somente uma câmera explicitamente escolhida e aprovada."""
        if self.camera_viewer is not None and self.camera_viewer.isVisible():
            self.camera_viewer.raise_()
            self.camera_viewer.activateWindow()
            return
        source_text, accepted = QInputDialog.getText(
            self, "Yuna • Câmera autorizada",
            "Selecione sua própria webcam (0, 1...) ou informe uma URL "
            "rtsp:// de câmera IP privada. Endereços com senha não são salvos:",
        )
        if not accepted or not source_text.strip():
            return
        try:
            source = parse_camera_source(source_text)
        except ValueError as exc:
            QMessageBox.warning(self, "Fonte de câmera inválida", str(exc))
            return
        approval = QMessageBox.question(
            self, "Permitir visualização por 5 minutos?",
            "A Yuna abrirá apenas " + source.label + ".\n"
            "Confirme que você possui autorização para visualizar esta câmera.\n"
            "Imagens não serão gravadas, analisadas nem enviadas à nuvem.\n"
            "A sessão dura no máximo 5 minutos e pode ser encerrada "
            "pelo botão Parar ou Break080111.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if approval != QMessageBox.StandardButton.Yes:
            return
        permission = CameraPermission()
        try:
            permission.authorize(source_text, approved=True, duration_seconds=300)
        except (ValueError, PermissionError) as exc:
            QMessageBox.warning(self, "Não foi possível autorizar", str(exc))
            return
        viewer = CameraViewer(permission, self)
        self.camera_viewer = viewer
        viewer.finished.connect(self._camera_closed)
        viewer.show()
        viewer.start_preview()
        self.status.setText(
            "Prévia de câmera autorizada • somente esta sessão • sem gravação"
        )

    def _camera_closed(self, *_args):
        self.camera_viewer = None

    def open_remote_camera_invitation(self):
        """Magi1020: convite para vídeo consentido, sem ligar webcams."""
        options = (
            "Criar convite privado para minha esposa",
            "Entrar com um convite que recebi",
        )
        selection, accepted = QInputDialog.getItem(
            self, "Yuna • Magi1020",
            "Videochamada opcional por serviço externo (Jitsi Meet).\n"
            "A câmera da outra pessoa só é compartilhada quando ela entra "
            "e autoriza o navegador. O que deseja fazer?",
            list(options), 0, False,
        )
        if not accepted:
            return
        if selection == options[0]:
            link = new_remote_camera_invite()
            popup = QMessageBox(self)
            popup.setWindowTitle("Magi1020 • Novo convite")
            popup.setIcon(QMessageBox.Icon.Information)
            popup.setText("Convite novo gerado para esta chamada.")
            popup.setInformativeText(
                "Link: " + link + "\n\n"
                "Envie esse link diretamente à sua esposa. Quem possui o "
                "link pode tentar entrar, então não o publique.\n\n"
                "Serviço EXTERNO: Jitsi Meet. Ao abrir, o site pode pedir "
                "login ao anfitrião e acesso à sua câmera/microfone. "
                "Sua esposa precisa entrar e liberar a webcam dela. "
                "A Yuna não controla essa câmera e não grava a chamada.\n\n"
                "Para encerrar a transmissão, cada participante deve usar "
                "'Sair' no próprio navegador; Break080111 na Yuna não "
                "desliga chamadas externas."
            )
            copy_button = popup.addButton(
                "Copiar convite", QMessageBox.ButtonRole.ActionRole)
            copy_open_button = popup.addButton(
                "Copiar e abrir", QMessageBox.ButtonRole.AcceptRole)
            popup.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
            popup.exec()
            chosen = popup.clickedButton()
            if chosen not in (copy_button, copy_open_button):
                return
            QApplication.clipboard().setText(link)
            if chosen == copy_open_button:
                if not QDesktopServices.openUrl(QUrl(link)):
                    self.status.setText(
                        "Convite copiado, mas o navegador não abriu."
                    )
                else:
                    self.status.setText(
                        "Magi1020 • convite copiado e videochamada aberta "
                        "no navegador externo"
                    )
            else:
                self.status.setText(
                    "Magi1020 • link copiado; envie à pessoa convidada "
                    "e abra a reunião com esse mesmo link"
                )
        elif selection == options[1]:
            link, confirmed = QInputDialog.getText(
                self, "Magi1020 • Entrar com convite",
                "Cole o link completo recebido da pessoa de confiança:",
            )
            if not confirmed:
                return
            try:
                safe_link = validate_remote_camera_invite(link)
            except ValueError:
                QMessageBox.warning(
                    self, "Convite não reconhecido",
                    "Aceitamos apenas convites Magi1020 no endereço "
                    "https://meet.jit.si. Solicite um novo convite."
                )
                return
            decision = QMessageBox.question(
                self, "Abrir chamada de vídeo externa?",
                "Você será direcionada(o) ao Jitsi Meet (serviço externo).\n"
                "O navegador pedirá permissão antes de usar sua webcam.\n"
                "Você pode manter a câmera desligada ou sair da chamada "
                "a qualquer momento. Deseja continuar?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if decision == QMessageBox.StandardButton.Yes:
                if not QDesktopServices.openUrl(QUrl(safe_link)):
                    self.status.setText("Não foi possível abrir a chamada no navegador.")
                else:
                    self.status.setText(
                        "Magi1020 • convite aberto; controle sua câmera pelo navegador"
                    )

    def send_message(self):
        content = self.composer.toPlainText().strip()
        if is_stop_request(content):
            self.composer.clear()
            self.emergency_stop()
            return
        if not self.pending_path and is_magi_camera_request(content):
            self.composer.clear()
            self.add_message(
                "Yuna", "Magi1020 reconhecido. Vou abrir as opções "
                "de convite de videochamada. A outra pessoa decide "
                "se compartilha sua câmera."
            )
            self.open_remote_camera_invitation()
            return
        if not self.pending_path and is_camera_view_request(content):
            self.composer.clear()
            self.add_message("Você", content)
            self.add_message("Yuna", "Posso abrir uma câmera sua ou autorizada, "
                             "mas primeiro preciso que você escolha a fonte e "
                             "confirme o acesso nesta sessão.")
            self.open_camera_viewer()
            return
        request = parse_voice_preference(content) if not self.pending_path else None
        if request:
            self.composer.clear()
            self.add_message("Você", content)
            self.apply_voice_preferences(request)
            return
        if not content and not self.pending_path:
            return
        self.composer.clear()
        self.set_busy(True)
        if self.pending_path:
            self.add_message(
                "Você", (content or "Analise este documento e destaque o mais útil.")
                + "\n[Anexo: " + self.pending_path.name + "]"
            )
            self.worker.analyze(self.pending_path, content)
        else:
            self.last_avatar_request = parse_avatar_request(content)
            if (self.last_avatar_request is not None
                    and (self.avatar_window is None
                         or not self.avatar_window.isVisible())):
                self.toggle_avatar()
            self.add_message("Você", content)
            self.worker.submit(content)


    def emergency_stop(self):
        """Interrompe áudio e ignora resposta em andamento, sem matar a thread."""
        self.worker.cancel_pending()
        self.game_session.stop()
        if self.camera_viewer is not None:
            self.camera_viewer.close()
        self.player.stop()
        self.voice_busy = False
        self._stop_avatar_speech()
        self.set_busy(False)
        self.status.setText("Parada solicitada • operações externas em curso podem continuar")
        self.add_message("Yuna", "Parei a voz e descartei as tarefas pendentes. "
                         "Uma operação já iniciada pode precisar terminar; "
                         "não vou afirmar que ela foi cancelada sem confirmação.")

    def clear_attachment(self):
        self.pending_path = None
        self.from_library = False
        self.attachment_notice.clear()
        self.attachment_notice.hide()
        self.remove_attachment.hide()
        self.save_attachment.setEnabled(False)
        self.status.setText("Anexo removido • pronto para conversar")

    def select_document(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Selecionar documento para a Yuna",
            str(Path.home() / "Documents"),
            "Documentos (*.docx *.xlsx *.pptx *.pdf *.txt *.md)"
        )
        if path:
            self.attach_document(path)

    def attach_document(self, filename):
        try:
            path = check_source(filename)
        except (ValueError, FileNotFoundError, OSError) as exc:
            QMessageBox.warning(self, "Anexo não aceito", str(exc))
            return
        self.pending_path = path
        self.from_library = False
        self.remove_attachment.show()
        self.attachment_notice.setText(
            "📎  " + path.name + "   •   Analise com Enviar ou guarde uma cópia com autorização."
        )
        self.attachment_notice.show()
        self.save_attachment.setEnabled(True)
        self.composer.setFocus()
        self.status.setText("Anexo selecionado • original não foi alterado")

    def use_library_document(self, item):
        try:
            self.pending_path = LIBRARY.path_for(item.data(Qt.ItemDataRole.UserRole))
            self.from_library = True
        except (ValueError, OSError, FileNotFoundError) as exc:
            self.show_error(str(exc))
            return
        self.attachment_notice.setText("📚  " + self.pending_path.name + " • da biblioteca pessoal")
        self.attachment_notice.show()
        self.remove_attachment.show()
        self.save_attachment.setEnabled(False)
        self.composer.setFocus()
        saved_notes = next(
            (row.get("notes", "") for row in LIBRARY.entries()
             if row.get("id") == item.data(Qt.ItemDataRole.UserRole)), ""
        )
        if saved_notes:
            self.add_message("Yuna", "Anotação que guardei sobre esse arquivo:\n" + saved_notes)

    def archive_document(self):
        if not self.pending_path or self.from_library:
            return
        answer = QMessageBox.question(
            self, "Guardar na biblioteca pessoal?",
            "Deseja criar uma cópia privada de '" + self.pending_path.name
            + "' em data/biblioteca?\n\n"
            "O original permanece no mesmo lugar. "
            "A Yuna não enviará o arquivo à internet.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        notes = (self.last_analysis if self.last_analysis_path == self.pending_path else "")
        self.set_busy(True)
        self.worker.archive(self.pending_path, notes)

    def saved_file(self, filename):
        self.set_busy(False)
        self.status.setText("Arquivo '" + filename + "' guardado na biblioteca local")
        self.add_message(
            "Yuna", "Guardei uma cópia de '" + filename
            + "' na minha biblioteca pessoal, com sua autorização. "
            "O arquivo original continua intacto."
        )

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and any(
            url.isLocalFile() for url in event.mimeData().urls()
        ):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        paths = [url.toLocalFile() for url in event.mimeData().urls()
                 if url.isLocalFile()]
        if paths:
            self.attach_document(paths[0])
            event.acceptProposedAction()

    def apply_voice_preferences(self, fields, *, speak_confirmation=True):
        """Aplica e salva preferências; não muda a aparência física do avatar."""
        try:
            updated = self.persona.updated(**fields)
            save_preferences(ROOT, updated)
        except (OSError, TypeError, ValueError):
            self.add_message("Yuna", "Não consegui salvar a preferência de voz. "
                             "Minhas configurações anteriores continuam válidas.")
            return False
        self.persona = updated
        current_index = {"feminina": 0, "masculina": 1, "neutra": 2}[
            updated.presentation]
        self.presentation_selector.blockSignals(True)
        self.presentation_selector.setCurrentIndex(current_index)
        self.presentation_selector.blockSignals(False)
        labels = {"feminina": "feminina", "masculina": "masculina",
                  "neutra": "sem preferência de gênero"}
        response = ("Salvei a preferência de voz " + labels[updated.presentation]
                    + " com estilo " + updated.voice_style + ". "
                    "Na opção Windows offline, a voz pt-BR correspondente "
                    "precisa estar instalada. Caso não exista, vou avisar "
                    "quando você testar. A aparência do avatar ainda "
                    "não muda com essa configuração.")
        self.status.setText("Preferência de voz salva • testar para ouvir")
        self.add_message("Yuna", response)
        if speak_confirmation:
            self.say("Preferência de voz atualizada. Esta é minha nova voz.")
        return True

    def presentation_changed(self, index):
        names = ("feminina", "masculina", "neutra")
        if 0 <= index < len(names):
            self.apply_voice_preferences(
                {"presentation": names[index]}, speak_confirmation=False)

    def voice_changed(self, index):
        if self._changing_voice:
            return
        if index == 2 and not self._edge_consent:
            consent = QMessageBox.question(
                self, "Voz online",
                "A voz Edge envia o texto da resposta a um serviço externo "
                "para síntese de fala. Não enviaremos conteúdo de documentos "
                "anexados por essa função.\n\nDeseja ativá-la?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if consent != QMessageBox.StandardButton.Yes:
                self._changing_voice = True
                self.voice_selector.setCurrentIndex(0)
                self._changing_voice = False
                self.voice_index = 0
                return
            self._edge_consent = True
        self.voice_index = index
        self.status.setText(
            ["Respostas por texto", "Voz Windows • offline",
             "Voz Edge • serviço externo autorizado"][index]
        )

    def test_voice(self):
        if self.voice_index == 0:
            self.status.setText("Escolha uma voz acima para iniciar o teste.")
            return
        if self.voice_busy:
            self.status.setText("A Yuna já está falando.")
            return
        if self.avatar_window is None:
            self.toggle_avatar()
        self.say("Olá! Esta é minha voz atual, com a boca sincronizada. Hehe!")

    def say(self, text, private=False):
        if self.voice_index == 0 or self.voice_busy:
            return
        mode = self.voice_index
        presentation = self.persona.presentation
        voice_style = self.persona.voice_style
        if private and mode == 2:
            # Apenas aviso genérico, nunca trechos do documento anexado.
            text = "A análise está pronta para ser lida na janela."
        if not speech_text(text):
            return
        self.voice_busy = True
        self.status.setText("Preparando a voz...")
        # A boca permanece parada durante a síntese; só começa com o player.

        def speak():
            try:
                if mode == 1:
                    result = synthesize_windows(text, presentation, voice_style)
                    if result:
                        self.signals.audio_ready.emit(str(result))
                    else:
                        self.signals.audio_error.emit("")
                elif mode == 2:
                    result = synthesize_edge(text, presentation, voice_style)
                    if result:
                        self.signals.audio_ready.emit(str(result))
                    else:
                        self.signals.audio_error.emit("")
            except Exception as exc:
                self.signals.audio_error.emit(str(exc))
        Thread(target=speak, daemon=True).start()

    def play_audio(self, path):
        self.audio_file = Path(path)
        self._audio_levels = (
            wave_envelope(self.audio_file)
            if self.audio_file.suffix.lower() == ".wav" else []
        )
        self.player.setSource(QUrl.fromLocalFile(str(self.audio_file)))
        self.player.play()
        self.status.setText("Iniciando reprodução da voz...")

    def _avatar_event(self, name, **payload):
        self._avatar_event_sequence += 1
        # MP3 não tem envelope PCM calculado; evitar exceção ao não ter amplitude.
        if name == "speech.level" and payload.get("amplitude") is None:
            payload["amplitude"] = 0.0
        accepted = self.avatar_controller.dispatch(
            name, sequence=self._avatar_event_sequence, **payload
        )
        if accepted and self.avatar_bridge is not None:
            self.avatar_bridge.publish(
                self.avatar_controller.snapshot, event=name,
                has_amplitude=bool(self._audio_levels),
                appearance=load_style(ROOT) if name in
                ("avatar.pose", "avatar.emotion") else None,
            )
        return accepted

    def _stop_avatar_speech(self):
        if self._active_speech_id is not None:
            self._avatar_event("speech.interrupted", speech_id=self._active_speech_id)
            self._active_speech_id = None
        if self.avatar_window is not None:
            self.avatar_window.set_speaking(False)

    def playback_state_changed(self, state):
        playing = (state == QMediaPlayer.PlaybackState.PlayingState
                   and self.voice_busy)
        if playing:
            if self._active_speech_id is None:
                self._speech_generation += 1
                self._active_speech_id = str(self._speech_generation)
                self._avatar_event("speech.started", speech_id=self._active_speech_id)
            if self.avatar_window is not None:
                self.avatar_window.set_speaking(True)
            self.status.setText("Yuna está falando...")
        else:
            self._stop_avatar_speech()

    def playback_position(self, position):
        if (self.player.playbackState() !=
                QMediaPlayer.PlaybackState.PlayingState):
            return
        if self._active_speech_id is None:
            return
        level = mouth_level_at(self._audio_levels, position)
        if self._avatar_event("speech.level", speech_id=self._active_speech_id,
                              position_ms=int(position), amplitude=level):
            if self.avatar_window is not None and self.avatar_window.isVisible():
                self.avatar_window.set_mouth_level(level)

    def playback_status(self, value):
        if value == QMediaPlayer.MediaStatus.EndOfMedia:
            self.player.stop()
            self.player.setSource(QUrl())
            self.cleanup_audio()
            self.voice_busy = False
            self._stop_avatar_speech()
            self.status.setText("Pronta • conversa local")

    def playback_error(self, error, detail):
        self.player.stop()
        self.player.setSource(QUrl())
        self.cleanup_audio()
        self.voice_error(detail or "A reprodução de voz falhou.")

    def cleanup_audio(self):
        self._audio_levels = []
        if self.audio_file:
            try:
                self.audio_file.unlink(missing_ok=True)
            except OSError:
                pass
            self.audio_file = None

    def voice_error(self, error):
        self.voice_busy = False
        self._audio_levels = []
        self._stop_avatar_speech()
        if error:
            self.status.setText("Voz indisponível: " + error[:180])
        else:
            self.status.setText("Pronta • conversa local")

    def request_microphone(self):
        if self.microphone_busy:
            return
        try:
            import importlib.util
            if (importlib.util.find_spec("sounddevice") is None
                    or importlib.util.find_spec("faster_whisper") is None):
                QMessageBox.information(
                    self, "Microfone opcional",
                    "Para usar o ditado de voz local, instale:\n"
                    "py -3 -m pip install -r requirements-voz.txt\n\n"
                    "Sem esses pacotes, a conversa por texto continua funcionando."
                )
                return
        except (ImportError, ValueError) as exc:
            self.status.setText("Microfone indisponível: " + str(exc))
            return
        confirm = QMessageBox.question(
            self, "Iniciar ditado local?",
            "A Yuna gravará 8 segundos do microfone após você confirmar "
            "e transcreverá localmente pelo Whisper. O áudio não será "
            "salvo em arquivo ou enviado para a internet.\n\n"
            "No primeiro uso, os pesos do modelo podem ser baixados "
            "da internet. Continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self.microphone_busy = True
        self.microphone_button.setEnabled(False)
        self.status.setText("🎙  Ouvindo por 8 segundos...")

        def recording():
            try:
                from speech_input import listen_once
                result = listen_once()
                self.signals.mic_ready.emit(result)
            except Exception as exc:
                self.signals.mic_error.emit(str(exc))
        Thread(target=recording, daemon=True).start()

    def microphone_ready(self, result):
        self.microphone_busy = False
        self.microphone_button.setEnabled(True)
        earlier = self.composer.toPlainText().strip()
        self.composer.setPlainText((earlier + "\n" if earlier else "") + result)
        self.composer.setFocus()
        self.status.setText("Ditado transcrito localmente • revise antes de enviar")

    def microphone_error(self, error):
        self.microphone_busy = False
        self.microphone_button.setEnabled(True)
        self.status.setText("Falha no microfone: " + str(error)[:180])

    def closeEvent(self, event):
        self.game_session.stop()
        if self.camera_viewer is not None:
            self.camera_viewer.close()
        if self.avatar_bridge is not None:
            self.avatar_bridge.stop()
            self.avatar_bridge = None
        if self.avatar_window is not None:
            self.avatar_window.close()
        self.worker.stop()
        self.player.stop()
        self.player.setSource(QUrl())
        self.cleanup_audio()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = YunaDesktop()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
