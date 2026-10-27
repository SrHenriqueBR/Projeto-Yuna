"""Janela-mascote 2D para Yuna. Iniciar com: py -3 yuna_overlay.py

Dependência da interface: PySide6. Sem câmera, microfone ou acesso oculto.
As ações existentes do Windows só são executadas por instruções diretas da pessoa.
"""
import os
from pathlib import Path
from queue import Queue
import sys
import time
from threading import Thread

from PySide6.QtCore import QObject, QPoint, Qt, QUrl, QTimer, Signal
from PySide6.QtGui import QPixmap, QFont, QTextCursor
from PySide6.QtWidgets import (
    QApplication, QDialog, QFileDialog, QComboBox, QHBoxLayout, QLabel, QLineEdit,
    QTextEdit, QPushButton, QVBoxLayout, QWidget
)
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

from computer import Computer
from initiative import looks_like_command
from self_model import about_text, is_self_question
from voice import speak_windows, synthesize_edge, synthesize_amanda, amanda_available, speech_text
from diary import DiaryStore, AUTO_INTERVAL_MINUTES, generate_entry
from screen_consent import ScreenConsent
from vision import describe_screen
from document_writer import (
    FileRequest, create_file, generate_contents, parse_file_request,
    looks_like_file_request, validate_title
)
from yuna import Memory, MODEL, ROOT, ask_model, declared_name, handle_message, startup_greeting
from office_agent import file_intent
from natural_interaction import classify_public_request
from natural_memory import parse_memory_intent
from self_model import VERSION
from own_initiative import pending_own_activity, propose_own_activity
from proactive import (
    NudgeSchedule, spontaneous_enabled, set_spontaneous, system_idle_seconds
)

ASSETS = ROOT / "assets"
POSES = ("idle", "wave", "happy", "thinking", "speaking", "sleepy")
DIARY_TASK = object()
FILE_TASK = "create_file"
SCREEN_TASK = object()
SPONTANEOUS_TASK = object()
SPONTANEOUS_SWITCH = "spontaneous_switch"


class Messages(QObject):
    message = Signal(str)
    listening = Signal(bool)
    speech = Signal(str)
    voice_finished = Signal(str)
    edge_ready = Signal(str)
    warning = Signal(str)
    diary_ready = Signal(str)
    diary_error = Signal(str)
    file_ready = Signal(str)
    file_failed = Signal(str)
    observed = Signal(str)
    plan_progress = Signal(str)
    spontaneous_state = Signal(bool)
    spontaneous_notice = Signal(str)


class DialogueThread(Thread):
    """SQLite fica exclusivamente nesta thread; nenhum compartilhamento de conexão."""
    def __init__(self, output):
        super().__init__(daemon=True)
        self.output = output
        self.inputs = Queue()

    def submit(self, text):
        self.inputs.put(text)

    def request_diary(self):
        self.inputs.put(DIARY_TASK)

    def request_screen(self):
        self.inputs.put(SCREEN_TASK)

    def request_file(self, request):
        self.inputs.put((FILE_TASK, request))

    def request_spontaneous(self):
        self.inputs.put(SPONTANEOUS_TASK)

    def set_spontaneous_mode(self, enabled):
        self.inputs.put((SPONTANEOUS_SWITCH, bool(enabled)))

    def stop(self):
        self.inputs.put(None)

    def run(self):
        try:
            memory = Memory(ROOT / "data" / "yuna.db")
            computer = Computer()
            self.output.spontaneous_state.emit(spontaneous_enabled(memory.initiative))
        except Exception as exc:
            self.output.warning.emit(f"Falha ao iniciar a Yuna: {exc}")
            return
        try:
            name = next((n for _, fact in reversed(memory.facts())
                         if (n := declared_name(fact))), "Kaizen")
            # A saudação usa o horário do Windows, não um clima inventado.
            greeting = startup_greeting()
            self.output.message.emit(greeting)
            self.output.speech.emit(greeting)
            while True:
                message = self.inputs.get()
                if message is None:
                    break
                if message is SPONTANEOUS_TASK:
                    if (spontaneous_enabled(memory.initiative)
                            and not pending_own_activity(memory.initiative)):
                        offer = propose_own_activity(memory.initiative)
                        self.output.spontaneous_notice.emit(
                            "Kaizen, tive uma ideia! 🖤\n\n" + offer
                        )
                    continue
                if (isinstance(message, tuple) and len(message) == 2
                        and message[0] == SPONTANEOUS_SWITCH):
                    set_spontaneous(memory.initiative, message[1])
                    self.output.spontaneous_state.emit(spontaneous_enabled(memory.initiative))
                    continue
                if message is SCREEN_TASK:
                    try:
                        self.output.observed.emit(describe_screen())
                    except Exception as exc:
                        self.output.warning.emit(f"Não consegui observar a tela: {exc}")
                    continue
                if message is DIARY_TASK:
                    try:
                        self.output.diary_ready.emit(generate_entry(ask_model))
                    except Exception as exc:
                        self.output.diary_error.emit(str(exc))
                    continue
                if isinstance(message, tuple) and len(message) == 2 and message[0] == FILE_TASK:
                    self.output.listening.emit(True)
                    try:
                        request = message[1]
                        content = generate_contents(request, ask_model)
                        target = create_file(request, content)
                        self.output.file_ready.emit(str(target))
                        self.output.speech.emit("Prontinho! Criei o seu documento.")
                    except Exception as exc:
                        self.output.file_failed.emit(str(exc))
                    finally:
                        self.output.listening.emit(False)
                    continue
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
                        answer = handle_message(memory, message, computer, progress=self.output.plan_progress.emit)
                    self.output.message.emit(answer)
                    if message.strip().casefold().startswith("/atividade"):
                        self.output.spontaneous_state.emit(spontaneous_enabled(memory.initiative))
                    # Não enviar caminho local completo para o serviço de voz online.
                    # Os diagnósticos podem incluir caminhos privados do computador.
                    # Também não transmitir caminhos completos à voz online.
                    if message.strip().casefold() in ("/versao", "/diagnostico"):
                        pass
                    elif (classify_public_request(message) is not None
                          or parse_memory_intent(message) is not None
                          or message.strip().casefold().startswith(("/github", "/melhorar", "/openai",
                                                              "/apis", "/api ", "/integracoes",
                                                              "/clima", "/livros", "/cep",
                                                              "/ias", "/ia ", "/provedores"))):
                        # Respostas de APIs, inclusive endereços e perguntas enviadas
                        # a outros modelos, ficam apenas no balão da Yuna.
                        self.output.speech.emit("Consulta finalizada. Veja o resultado na tela.")
                    elif message.strip().casefold().startswith(("/github", "/melhorar", "/openai")):
                        # Código e resultados de integrações ficam só na interface;
                        # não repassar conteúdos e caminhos ao serviço online de voz.
                        self.output.speech.emit("Concluí sua consulta. Confira a resposta no balão.")
                    elif answer.startswith("✅ Plano concluído"):
                        self.output.speech.emit("Concluí seu plano e verifiquei o arquivo. Confira o resultado na janela.")
                    elif file_intent(message):
                        self.output.speech.emit("Veja na janela se seu arquivo foi realmente criado.")
                    elif message.strip().casefold() == "/teste_arquivo":
                        self.output.speech.emit("Teste de gravação concluído. Confira o arquivo na Área de Trabalho.")
                    else:
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


class DiaryWindow(QWidget):
    """Leitor simples: a escrita aparece aos poucos e é guardada em Markdown."""
    def __init__(self, mascot):
        super().__init__()
        self.mascot = mascot
        self.setWindowTitle("📖 Diário da Yuna — ficção gerada pelo Ollama")
        self.resize(490, 590)
        self.setStyleSheet(
            "QWidget {background:#171125;color:#efe4ff;}"
            "QTextEdit {background:#221a35;border:1px solid #6b448a;"
            "border-radius:12px;padding:10px;font-size:13px;}"
            "QPushButton {background:#4c316b;border-radius:10px;padding:10px;}"
        )
        root = QVBoxLayout(self)
        heading = QLabel("☾ As páginas da Escuridão")
        heading.setStyleSheet("font-size:19px;font-weight:700;")
        root.addWidget(heading)
        note = QLabel(
            "Reflexões ficcionais, não sentimentos reais. Arquivo salvo localmente.\n"
            "A escrita automática fica desligada até você ativar."
        )
        note.setWordWrap(True)
        root.addWidget(note)
        self.display = QTextEdit()
        self.display.setReadOnly(True)
        root.addWidget(self.display, 1)
        actions = QHBoxLayout()
        self.write_button = QPushButton("✍ Escrever agora")
        self.write_button.clicked.connect(mascot.request_diary)
        actions.addWidget(self.write_button)
        self.auto_button = QPushButton()
        self.auto_button.clicked.connect(mascot.toggle_diary_auto)
        actions.addWidget(self.auto_button)
        root.addLayout(actions)
        self.status = QLabel("")
        self.status.setWordWrap(True)
        root.addWidget(self.status)
        self.refresh()

    def refresh(self):
        self.display.setPlainText(self.mascot.diary_store.read())
        scroll = self.display.verticalScrollBar()
        scroll.setValue(scroll.maximum())
        self.auto_button.setText(
            "⏹ Desligar automático" if self.mascot.diary_store.auto_enabled
            else "▶ Ativar automático"
        )

    def update_progress(self, message):
        self.status.setText(message)


class FileCreatorDialog(QDialog):
    """A pessoa escolhe destino e conteúdo; o modelo não controla o caminho."""
    def __init__(self, mascot):
        super().__init__(mascot)
        self.mascot = mascot
        self.setWindowTitle("📄 Criar documento com a Yuna")
        self.setMinimumWidth(480)
        self.setStyleSheet(
            "QDialog {background:#1b152c;color:#f5eaff;}"
            "QLineEdit, QComboBox {background:#2b2042;color:white;"
            "border:1px solid #76569b;border-radius:9px;padding:10px;}"
            "QPushButton {background:#523372;color:white;border-radius:9px;padding:10px;}"
        )
        root = QVBoxLayout(self)
        root.addWidget(QLabel("📄 Que arquivo vamos criar, Kaizen?"))
        root.addWidget(QLabel("Formato:"))
        self.format = QComboBox()
        self.format.addItem("Word (.docx)", "word")
        self.format.addItem("Texto (.txt)", "texto")
        self.format.addItem("Markdown (.md)", "markdown")
        root.addWidget(self.format)
        root.addWidget(QLabel("Nome do documento:"))
        self.title = QLineEdit()
        self.title.setPlaceholderText("Ex.: Diário da Yuna")
        root.addWidget(self.title)
        root.addWidget(QLabel("O que a Yuna deve escrever?"))
        self.description = QLineEdit()
        self.description.setPlaceholderText("Ex.: Uma primeira página de diário da personagem")
        root.addWidget(self.description)
        root.addWidget(QLabel("Pasta onde salvar:"))
        self.folder = QLineEdit()
        self.folder.setText(str(Path.home() / "Documents"))
        self.folder.setReadOnly(True)
        root.addWidget(self.folder)
        browse = QPushButton("📂 Escolher pasta...")
        browse.clicked.connect(self.choose_folder)
        root.addWidget(browse)
        self.create_button = QPushButton("✨ Criar arquivo")
        self.create_button.clicked.connect(self.create)
        root.addWidget(self.create_button)
        self.feedback = QLabel("O arquivo só será salvo depois que você confirmar.")
        self.feedback.setWordWrap(True)
        root.addWidget(self.feedback)

    def choose_folder(self):
        selected = QFileDialog.getExistingDirectory(
            self, "Escolha onde salvar o arquivo", self.folder.text()
        )
        if selected:
            self.folder.setText(selected)

    def create(self):
        try:
            title = validate_title(self.title.text())
            directory = Path(self.folder.text())
            if not directory.is_dir():
                raise ValueError("Escolha uma pasta existente para salvar.")
            description = self.description.text().strip()
            if len(description) > 500:
                raise ValueError("Descreva o documento usando no máximo 500 caracteres.")
            request = FileRequest(
                kind=self.format.currentData(),
                title=title,
                directory=directory,
                description=description,
            )
            self.create_button.setEnabled(False)
            self.feedback.setText("Ollama está escrevendo e salvando o arquivo...")
            self.mascot.dialogue.request_file(request)
        except ValueError as exc:
            self.feedback.setText(str(exc))

    def file_done(self, message, ok):
        self.create_button.setEnabled(True)
        self.feedback.setText(message)
        if ok:
            self.title.clear()
            self.description.clear()


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
        self.spontaneous_enabled = True
        self.spontaneous_schedule = NudgeSchedule.start(time.monotonic())
        self.frame_index = 0
        self.last_expression = "idle"
        self.temp_mp3 = None
        self.pixmaps = {}
        self.diary_store = DiaryStore(ROOT / "data")
        self.screen_consent = ScreenConsent(ROOT / "data")
        self.screen_confirm_pending = False
        self.diary_window = None
        self.file_window = None
        self.diary_pending = False
        self.diary_buffer = ""
        self.diary_position = 0
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
        if self.screen_consent.enabled:
            # Uma observação por início de sessão, enviada somente ao Ollama local.
            self.dialogue.request_screen()
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.animate_pose)
        self.animation_timer.start(360)
        self.diary_typing_timer = QTimer(self)
        self.diary_typing_timer.setInterval(70)
        self.diary_typing_timer.timeout.connect(self.type_diary)
        self.diary_auto_timer = QTimer(self)
        self.diary_auto_timer.setInterval(AUTO_INTERVAL_MINUTES * 60 * 1000)
        self.diary_auto_timer.timeout.connect(self.auto_diary)
        if self.diary_store.auto_enabled:
            self.diary_auto_timer.start()
        self.spontaneous_timer = QTimer(self)
        self.spontaneous_timer.setInterval(60 * 1000)
        self.spontaneous_timer.timeout.connect(self.check_spontaneous)
        self.spontaneous_timer.start()

    def setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(11, 8, 11, 5)
        root.setSpacing(7)
        top = QHBoxLayout()
        voice_row = QHBoxLayout()
        title = QLabel(f"☾ YUNA {VERSION}")
        title.setStyleSheet(
            "color:#e9d5ff;font-size:14px;font-weight:800;"
            "background:#1c1730;border:1px solid #513c6d;border-radius:12px;padding:8px"
        )
        top.addWidget(title)
        top.addStretch()
        self.vision_button = QPushButton()
        self.vision_button.setToolTip("Visão local da tela ao iniciar (opt-in)")
        self.vision_button.clicked.connect(self.toggle_screen)
        top.addWidget(self.vision_button)
        self.update_vision_button()
        self.copy_button = QPushButton("📋")
        self.copy_button.setToolTip("Copiar o texto completo da resposta")
        self.copy_button.setFixedWidth(35)
        self.copy_button.clicked.connect(self.copy_answer)
        top.addWidget(self.copy_button)
        self.diary_button = QPushButton("📖")
        self.diary_button.setToolTip("Abrir diário local da Yuna")
        self.diary_button.setFixedWidth(35)
        self.diary_button.clicked.connect(self.open_diary)
        top.addWidget(self.diary_button)
        self.file_button = QPushButton("📄")
        self.file_button.setToolTip("Criar Word, texto ou Markdown na pasta que você escolher")
        self.file_button.setFixedWidth(35)
        self.file_button.clicked.connect(self.open_file_creator)
        top.addWidget(self.file_button)
        self.spontaneous_button = QPushButton("💬 Ativa")
        self.spontaneous_button.setToolTip(
            "Yuna sugere atividades após um tempo sem conversa. Clique para pausar."
        )
        self.spontaneous_button.clicked.connect(self.toggle_spontaneous)
        voice_row.addWidget(self.spontaneous_button)
        self.voice_button = QPushButton()
        self.voice_button.setToolTip("Alternar voz: Windows offline, Edge online, sem voz")
        self.voice_button.clicked.connect(self.cycle_voice)
        voice_row.addWidget(self.voice_button)
        self.amanda_button = QPushButton("🎙 Amanda")
        self.amanda_button.setToolTip("Ativar Amanda Kelly (ElevenLabs, requer chave API)")
        self.amanda_button.clicked.connect(self.select_amanda)
        voice_row.addWidget(self.amanda_button)
        # Confirmação dentro da mascote: evita que janelas modais fechem um Qt.Tool.
        self.cancel_voice_button = QPushButton("Cancelar")
        self.cancel_voice_button.clicked.connect(self.cancel_voice_consent)
        self.cancel_voice_button.hide()
        voice_row.addWidget(self.cancel_voice_button)
        close = QPushButton("×")
        close.setFixedWidth(30)
        close.clicked.connect(self.close)
        top.addWidget(close)
        root.addLayout(top)
        voice_row.addStretch()
        root.addLayout(voice_row)
        self.update_voice_button()

        self.bubble = QTextEdit()
        self.bubble.setPlainText("Iniciando minha memória... ✦")
        self.bubble.setReadOnly(True)
        self.bubble.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.bubble.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.bubble.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.bubble.setMinimumHeight(100)
        self.bubble.setMaximumHeight(160)
        self.bubble.setStyleSheet(
            "QTextEdit { background-color: rgba(28, 20, 46, 235); color: #f6efff;"
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

        for button in (self.vision_button, self.copy_button, self.diary_button, self.file_button, self.spontaneous_button, self.voice_button, self.amanda_button, self.cancel_voice_button, close, self.send_button):
            button.setStyleSheet(
                "QPushButton {background:#42275d;color:#f8f0ff;border-radius:10px;"
                "border:1px solid #765097;padding:9px;font-weight:600}"
                "QPushButton:hover {background:#5d3680}"
            )

    def open_file_creator(self):
        if self.file_window is None:
            self.file_window = FileCreatorDialog(self)
        self.file_window.show()
        self.file_window.raise_()
        self.file_window.activateWindow()

    def file_created(self, path):
        self.show_message(f"Documento criado! Salvei em: {path}")
        self.status.setText("Arquivo salvo localmente")
        if self.file_window:
            self.file_window.file_done(f"✅ Salvo em: {path}", True)

    def file_failed(self, error):
        self.show_message(f"Não consegui criar o documento: {error}")
        self.status.setText("Falha ao criar documento")
        if self.file_window:
            self.file_window.file_done(f"❌ {error}", False)

    def open_diary(self):
        if self.diary_window is None:
            self.diary_window = DiaryWindow(self)
        self.diary_window.refresh()
        self.diary_window.show()
        self.diary_window.raise_()
        self.diary_window.activateWindow()

    def toggle_diary_auto(self):
        enabled = not self.diary_store.auto_enabled
        try:
            self.diary_store.set_auto(enabled)
        except OSError as exc:
            self.diary_error(str(exc))
            return
        if enabled:
            self.diary_auto_timer.start()
        else:
            self.diary_auto_timer.stop()
        if self.diary_window:
            self.diary_window.refresh()
            self.diary_window.update_progress(
                f"Escrita automática {'ativada' if enabled else 'desativada'}. "
                f"Uma reflexão a cada {AUTO_INTERVAL_MINUTES} minutos com a Yuna aberta."
            )

    def request_diary(self):
        if self.diary_pending:
            if self.diary_window:
                self.diary_window.update_progress("Já estou escrevendo ou elaborando uma nota.")
            return
        self.diary_pending = True
        self.dialogue.request_diary()
        if self.diary_window:
            self.diary_window.update_progress("Ollama: elaborando uma reflexão...")
        self.status.setText("Diário: criando reflexão local...")

    def auto_diary(self):
        # Não interrompe conversas ou escritas em andamento.
        if self.diary_store.auto_enabled and not self.thinking and not self.diary_pending:
            self.request_diary()

    def diary_ready(self, entry):
        try:
            self.diary_store.start_entry()
            self.diary_buffer = entry
            self.diary_position = 0
            if self.diary_window:
                self.diary_window.refresh()
                self.diary_window.update_progress("Escrevendo lentamente no arquivo...")
            self.diary_typing_timer.start()
            self.status.setText("Diário: escrevendo uma nova página...")
        except (OSError, RuntimeError) as exc:
            self.diary_error(str(exc))

    def type_diary(self):
        if self.diary_position >= len(self.diary_buffer):
            self.diary_typing_timer.stop()
            try:
                self.diary_store.end_entry()
            except (OSError, RuntimeError) as exc:
                self.diary_error(str(exc))
                return
            self.diary_pending = False
            self.diary_buffer = ""
            if self.diary_window:
                self.diary_window.refresh()
                self.diary_window.update_progress("Entrada concluída e salva em data/diario_yuna.md.")
            self.status.setText("Diário salvo localmente")
            return
        piece = self.diary_buffer[self.diary_position:self.diary_position + 5]
        try:
            self.diary_store.write_piece(piece)
        except (OSError, RuntimeError) as exc:
            self.diary_error(str(exc))
            return
        self.diary_position += len(piece)
        if self.diary_window and self.diary_window.isVisible():
            self.diary_window.refresh()

    def diary_error(self, message):
        self.diary_typing_timer.stop()
        self.diary_pending = False
        self.diary_buffer = ""
        self.status.setText(f"Diário: {message[:115]}")
        if self.diary_window:
            self.diary_window.update_progress(f"Não consegui escrever: {message[:200]}")

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
        self.signals.diary_ready.connect(self.diary_ready)
        self.signals.diary_error.connect(self.diary_error)
        self.signals.file_ready.connect(self.file_created)
        self.signals.file_failed.connect(self.file_failed)
        self.signals.observed.connect(self.screen_observed)
        self.signals.plan_progress.connect(self.show_plan_progress)
        self.signals.spontaneous_state.connect(self.update_spontaneous_state)
        self.signals.spontaneous_notice.connect(self.display_spontaneous)

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

    def update_vision_button(self):
        if self.screen_confirm_pending:
            self.vision_button.setText("✓ Visão")
        else:
            self.vision_button.setText(
                "👁 On" if self.screen_consent.enabled else "👁 Off"
            )

    def toggle_screen(self):
        if self.screen_consent.enabled:
            self.screen_consent.set_enabled(False)
            self.screen_confirm_pending = False
            self.update_vision_button()
            self.status.setText("Visão inicial desativada. Nenhuma nova captura automática.")
            return
        if not self.screen_confirm_pending:
            self.screen_confirm_pending = True
            self.update_vision_button()
            self.bubble.setPlainText(
                "Ativar observação inicial? Ao abrir a Yuna, uma imagem da tela "
                "será enviada SOMENTE ao seu Ollama local se houver modelo "
                "de visão configurado. A captura pode conter dados pessoais "
                "visíveis. Clique novamente em ✓ Visão para confirmar; "
                "para cancelar, feche e reabra a Yuna."
            )
            return
        self.screen_confirm_pending = False
        self.screen_consent.set_enabled(True)
        self.update_vision_button()
        self.status.setText("Visão inicial ativada. Captura local solicitada.")
        self.dialogue.request_screen()

    def screen_observed(self, result):
        self.show_message("Visão inicial (uma captura local):\n" + result)
        self.status.setText("Visão inicial concluída · câmera e microfone seguem desligados")

    def copy_answer(self):
        text = self.latest_message or self.bubble.toPlainText()
        QApplication.clipboard().setText(text)
        self.status.setText("Texto da resposta copiado para a área de transferência")

    def update_spontaneous_state(self, enabled):
        self.spontaneous_enabled = bool(enabled)
        self.spontaneous_button.setText("💬 Ativa" if enabled else "💤 Pausada")
        self.spontaneous_button.setToolTip(
            "Pausar as iniciativas espontâneas da Yuna"
            if enabled else "Ativar as iniciativas espontâneas da Yuna"
        )

    def toggle_spontaneous(self):
        self.spontaneous_schedule.user_active(time.monotonic())
        self.dialogue.set_spontaneous_mode(not self.spontaneous_enabled)

    def check_spontaneous(self):
        busy = (
            self.thinking or self.voice_busy or self.voice_confirm_pending
            or self.screen_confirm_pending or self.diary_pending
            or self.diary_typing_timer.isActive()
            or bool(self.entry.text().strip())
            or bool(self.diary_window and self.diary_window.isVisible())
            or not self.isVisible()
        )
        now = time.monotonic()
        if self.spontaneous_schedule.ready(
            now, system_idle_seconds(),
            enabled=self.spontaneous_enabled, busy=busy
        ):
            self.spontaneous_schedule.mark_notice(now)
            self.dialogue.request_spontaneous()

    def display_spontaneous(self, message):
        if (self.thinking or self.voice_busy or self.voice_confirm_pending
                or self.screen_confirm_pending or self.entry.text().strip()):
            return
        self.show_message(message)
        self.status.setText("Yuna tomou iniciativa · diga 'pode fazer' ou 'agora não'")
        # Texto pré-definido, sem dados pessoais. Voz permanece opcional.
        self.say("Kaizen, tive uma ideia! Quer ouvir?")

    def show_plan_progress(self, step):
        self.bubble.setPlainText("Yuna 0.13 · Executando plano\n" + step)
        self.status.setText(step[:100])
        self.show_expression("thinking")

    def show_message(self, text):
        self.latest_message = text
        # Nunca sobrescrever o aviso de privacidade enquanto a confirmação está pendente.
        if self.voice_confirm_pending:
            return
        self.bubble.setPlainText(text)
        self.bubble.moveCursor(QTextCursor.MoveOperation.Start)
        self.bubble.setToolTip("Role para ler a resposta inteira ou clique em 📋 para copiar.")
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
        self.spontaneous_schedule.user_active(time.monotonic())
        self.bubble.setPlainText("Hmm, deixa eu pensar nisso... ✦")
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
        self.bubble.setPlainText(
            self.latest_message[:450] if self.latest_message
            else "Beleza! A voz anterior continua selecionada. 🖤"
        )
        self.status.setText("Voz anterior mantida. Nenhum texto novo foi enviado à API.")

    def request_voice_consent(self, selected):
        if selected == "amanda" and not amanda_available():
            self.status.setText("Amanda Kelly precisa da chave ELEVENLABS_API_KEY.")
            self.bubble.setPlainText(
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
        self.bubble.setPlainText(warning)
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
            self.bubble.setPlainText(
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
        self.show_message("Não consegui executar a ação: " + error)
        self.status.setText("Falha na ação · veja a mensagem no balão")

    def closeEvent(self, event):
        self.spontaneous_timer.stop()
        self.diary_typing_timer.stop()
        self.diary_auto_timer.stop()
        if self.diary_window is not None:
            self.diary_window.close()
        if self.file_window is not None:
            self.file_window.close()
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
