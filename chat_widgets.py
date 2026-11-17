"""Texto de chat formatado sem HTML ativo, imagens remotas ou execução de código."""
import ipaddress
import re
from urllib.parse import urlsplit

from PySide6.QtCore import QByteArray, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QTextDocument
from PySide6.QtWidgets import (QApplication, QComboBox, QFrame, QHBoxLayout,
    QLabel, QPlainTextEdit, QPushButton, QTextBrowser, QVBoxLayout)

MARKDOWN = (QTextDocument.MarkdownFeature.MarkdownDialectGitHub |
            QTextDocument.MarkdownFeature.MarkdownNoHTML)
MAX_DISPLAY = 96000


def code_blocks(text):
    """Extrai somente cercas fechadas, mantendo quebras e indentação do código."""
    blocks = []
    fence = None
    lines = []
    language = ""
    for line in text.splitlines(keepends=True):
        if fence is None:
            match = re.match(r"^ {0,3}(`{3,}|~{3,})([^\r\n]*)[\r\n]*$", line)
            if match:
                fence = match.group(1)
                language = match.group(2).strip().split(" ", 1)[0][:24]
                lines = []
        elif re.fullmatch(r" {0,3}" + re.escape(fence[0]) + "{" + str(len(fence)) + r",}[ \t\r\n]*", line):
            blocks.append((language, "".join(lines)))
            fence = None
        else:
            lines.append(line)
    return blocks


def public_link(value):
    if len(value) > 2048 or any(ord(c) < 32 for c in value) or "\\" in value:
        return False
    try:
        parsed = urlsplit(value)
        host = (parsed.hostname or "").rstrip(".")
        if parsed.scheme not in ("https", "http") or not host or parsed.username or parsed.password:
            return False
        if (parsed.port not in (None, 80, 443) or host == "localhost.localdomain"
                or host.endswith((".local", ".localhost", ".internal")) or "." not in host):
            return False
        try:
            return ipaddress.ip_address(host).is_global
        except ValueError:
            # Nomes locais e notações numéricas alternativas não são links de fontes públicas.
            return not re.fullmatch(r"[0-9.]+", host) and not host.startswith("0x")
    except ValueError:
        return False


class SafeDocument(QTextDocument):
    def loadResource(self, resource_type, name):
        return QByteArray()


def markdown_html(text):
    document = SafeDocument()
    value = str(text)
    if len(value) > MAX_DISPLAY:
        value = value[:MAX_DISPLAY] + "\n\n[Prévia limitada. Use Copiar resposta para obter o texto completo.]"
    document.setMarkdown(value, MARKDOWN)
    rendered = document.toHtml()
    # O fragmento conserva listas/tabelas/código, sem repetir <html> em cada mensagem.
    return rendered.split("<body", 1)[1].split(">", 1)[1].rsplit("</body>", 1)[0]


class SafeBrowser(QTextBrowser):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDocument(SafeDocument(self))
        self.setOpenLinks(False)
        self.setOpenExternalLinks(False)
        self.anchorClicked.connect(self.open_public_link)

    def loadResource(self, resource_type, name):
        return QByteArray()

    def open_public_link(self, url):
        value = url.toString()
        if public_link(value):
            QDesktopServices.openUrl(QUrl(value))


class MessageCard(QFrame):
    def __init__(self, author, content, *, accent=False, teach=None, parent=None):
        super().__init__(parent)
        self.original = str(content)
        self.blocks = code_blocks(self.original)
        is_user = author in ("Você", "Kaizen")
        background = "#41305d" if is_user else "#242132"
        border = "#7259b2" if is_user else "#36304f"
        self.setMaximumWidth(760)
        self.setStyleSheet(
            f"MessageCard {{background:{background};border:1px solid {border};border-radius:14px;}}"
            "QTextBrowser {background:transparent;border:0;color:#f3f0fa;font-size:13px;}"
            "QPushButton {padding:5px 9px;font-size:11px;} QComboBox {padding:4px;font-size:11px;}")
        box = QVBoxLayout(self)
        box.setContentsMargins(14, 10, 14, 10)
        label = QLabel("Yuna • documento" if accent else author)
        label.setStyleSheet("color:#d9c5ff;font-size:11px;font-weight:700;background:transparent;")
        box.addWidget(label)
        self.browser = SafeBrowser()
        self.browser.setMinimumWidth(120)
        if is_user:
            self.browser.setPlainText(self.original)
        else:
            self.browser.setHtml(markdown_html(self.original))
        box.addWidget(self.browser)
        row = QHBoxLayout()
        self.copy = QPushButton("Copiar" if is_user else "Copiar resposta")
        self._copy_label = self.copy.text()
        self._copy_timer = QTimer(self)
        self._copy_timer.setSingleShot(True)
        self._copy_timer.timeout.connect(lambda: self.copy.setText(self._copy_label))
        self.copy.clicked.connect(lambda: self.copy_text(self.original))
        row.addWidget(self.copy)
        if self.blocks:
            self.code_selector = QComboBox()
            for i, (language, _) in enumerate(self.blocks, 1):
                self.code_selector.addItem(f"Código {i}" + (" · " + language if language else ""))
            self.code_copy = QPushButton("Copiar código")
            self.code_copy.clicked.connect(lambda: self.copy_text(self.blocks[self.code_selector.currentIndex()][1]))
            row.addWidget(self.code_selector)
            row.addWidget(self.code_copy)
        if teach is not None and not is_user and not accent:
            self.teach = QPushButton("Corrigir e ensinar")
            self.teach.clicked.connect(teach)
            row.addWidget(self.teach)
        row.addStretch()
        box.addLayout(row)
        self.browser.document().documentLayout().documentSizeChanged.connect(self.fit)
        QTimer.singleShot(0, self.fit)

    def copy_text(self, value):
        QApplication.clipboard().setText(value)
        self.copy.setText("Copiado ✓")
        self._copy_timer.start(1500)

    def fit(self, *_):
        height = int(self.browser.document().size().height()) + 16
        height = max(48, min(460, height))
        if self.browser.height() != height:
            self.browser.setFixedHeight(height)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(0, self.fit)


class LiveAnswer(QFrame):
    """Prévia transitória; só a resposta final revisada entra no histórico."""
    def __init__(self, parent=None, *, max_height=130):
        super().__init__(parent)
        self.setStyleSheet("QFrame {background:#211e2d;border:1px solid #594574;border-radius:9px;}"
                           "QLabel,QPlainTextEdit {background:transparent;border:0;color:#e6d9ff;}")
        box = QVBoxLayout(self)
        box.setContentsMargins(10, 6, 10, 6)
        label = QLabel("Yuna está escrevendo • prévia ainda não salva")
        label.setWordWrap(True)
        box.addWidget(label)
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        self.text.setMinimumHeight(48)
        self.text.setMaximumHeight(max_height)
        box.addWidget(self.text)
        self.hide()

    def update_text(self, content):
        if not content:
            self.clear()
            return
        bar = self.text.verticalScrollBar()
        follow = bar.value() >= bar.maximum() - 8
        position = bar.value()
        self.text.setPlainText(content)
        bar.setValue(bar.maximum() if follow else position)
        self.show()

    def clear(self):
        self.text.clear()
        self.hide()
