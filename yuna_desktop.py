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
