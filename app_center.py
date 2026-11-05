"""Uma Central para recursos, permissões e manutenção da mesma Yuna."""
from pathlib import Path
from threading import Thread

from PySide6.QtCore import Qt, Signal, QUrl, QTimer
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QCheckBox, QDialog, QHBoxLayout, QLabel,
    QMessageBox, QPushButton, QTabWidget, QTextBrowser, QVBoxLayout, QWidget)

from app_tools import (TOOLS, RELEASE_URL, configure_shortcuts, installation_status,
                       launch_tool, prepare_model)
from self_model import VERSION
from model_config import MODEL_OPTIONS, LEGACY_OPTIONS, load_selected_model


class YunaCenter(QDialog):
    finished_job = Signal(bool, str)
    progress = Signal(str)

    def __init__(self, controller, root):
        super().__init__(controller.window)
        self.controller = controller
        self.root = Path(root)
        self.running = False
        self.setWindowTitle("Central da Yuna")
        self.resize(650, 620)
        self.setMinimumSize(520, 500)
        self.setStyleSheet("""
            QDialog, QWidget { background: #16151e; color: #eeeaf7; }
            QLabel { background: transparent; }
            QPushButton { background: #302a43; border: 1px solid #55456f;
                border-radius: 8px; padding: 10px; text-align: left; }
            QPushButton:hover { background: #44365e; }
            QPushButton:disabled { color: #85808f; }
            QTabWidget::pane { border: 1px solid #393145; border-radius: 8px; }
            QTabBar::tab { background: #24202e; padding: 10px 15px; }
            QTabBar::tab:selected { background: #544073; }
            QTextBrowser { border: 1px solid #393145; border-radius: 8px; padding: 8px; }
            QCheckBox { padding: 8px; }
        """)
        layout = QVBoxLayout(self)
        title = QLabel(f"✦  Yuna {VERSION}")
        title.setStyleSheet("font-size: 24px; font-weight: 600; color: #d5baff;")
        layout.addWidget(title)
        layout.addWidget(QLabel("Conversa, recursos e configurações em um só lugar."))
        tabs = QTabWidget()
        layout.addWidget(tabs)
        home, permissions, maintenance, advanced = [QWidget() for _ in range(4)]
        for page, label in zip((home, permissions, maintenance, advanced),
                               ("Minha Yuna", "Permissões", "Preparação", "Avançado")):
            tabs.addTab(page, label)
        box = QVBoxLayout(home)
        self.button(box, "Conversar no chat compacto", controller.show_compact)
        self.button(box, "Abrir janela completa e documentos", controller.show_full)
        self.button(box, "Mostrar ou esconder a personagem 2D", controller.window.toggle_avatar)
        self.button(box, "Abrir avatar 3D", lambda: self.open_tool("3d"))
        self.button(box, "Conversar no navegador deste computador", lambda: self.open_tool("web"))
        self.button(box, "Recolher para segundo plano", self.hide_companion)
        box.addStretch()
        box = QVBoxLayout(permissions)
        text = QLabel("Você controla os recursos. Microfone e câmera pedem autorização nesta sessão.")
        text.setWordWrap(True)
        box.addWidget(text)
        self.wake = self.action_checkbox(box, "Escutar “Olá Yuna”", controller.wake_action)
        self.usb = self.action_checkbox(box, "Perceber USB e energia", controller.plug_action)
        self.plug_voice = self.action_checkbox(box, "Falar avisos de conexões", controller.plug_voice)
        self.button(box, "Abrir câmera e escolher a fonte…", controller.window.open_camera_viewer)
        self.button(box, "Autorizar um jogo nesta sessão…", controller.configure_game)
        self.button(box, "Interromper ações e microfone", controller.window.emergency_stop)
        note = QLabel("Operações bancárias continuam desativadas. A Central não concede controle irrestrito ao modelo.")
        note.setWordWrap(True)
        box.addWidget(note)
        box.addStretch()
        box = QVBoxLayout(maintenance)
        self.button(box, "Verificar instalação e Ollama", lambda: self.job(lambda: installation_status(self.root)))
        model_note = QLabel(
            "✦ Qwen3.5 GRATUITO • modelos instalados no seu computador via Ollama. "
            "Sem conta de nuvem, chave de API ou cobrança por conversas. "
            "A seleção só muda quando o download termina; reinicie a Yuna."
        )
        model_note.setWordWrap(True)
        box.addWidget(model_note)
        for model, label, description in MODEL_OPTIONS:
            self.button(
                box, "⬇  Qwen3.5 " + label + "  (" + model + ")",
                lambda checked=False, name=model: self.download_model(name)
            ).setToolTip(description + " · sem API paga")
        old_label = QLabel("Compatibilidade: modelos da versão anterior")
        old_label.setStyleSheet("color:#a89cbf; font-size:11px;")
        box.addWidget(old_label)
        row = QHBoxLayout()
        for model, label in LEGACY_OPTIONS:
            self.button(
                row, label, lambda checked=False, name=model: self.download_model(name)
            ).setToolTip(model)
        box.addLayout(row)
        self.current_model_label = QLabel(
            "Modelo selecionado: " + load_selected_model(self.root)
            + " (a troca precisa de reinicialização)"
        )
        self.current_model_label.setWordWrap(True)
        box.addWidget(self.current_model_label)
        self.button(box, "Instalar ou abrir o site do Ollama", lambda: QDesktopServices.openUrl(QUrl("https://ollama.com/download/windows")))
        self.button(box, "Criar ou reparar atalhos Yuna", lambda: self.job(lambda: configure_shortcuts(self.root)))
        row = QHBoxLayout()
        self.button(row, "Iniciar com Windows", lambda: self.set_startup(True))
        self.button(row, "Não iniciar com Windows", lambda: self.set_startup(False))
        box.addLayout(row)
        self.button(box, "Abrir pasta das memórias", self.open_data)
        self.button(box, "Atualizar ou reparar o app", lambda: QDesktopServices.openUrl(QUrl(RELEASE_URL)))
        box.addStretch()
        box = QVBoxLayout(advanced)
        label = QLabel("Ferramentas de manutenção. As janelas de console mostram o andamento e esperam Enter antes de fechar.")
        label.setWordWrap(True)
        box.addWidget(label)
        for key in ("autoteste", "terminal", "laboratorio", "revisar", "gestao", "mascote"):
            self.button(box, TOOLS[key][0], lambda checked=False, key=key: self.open_tool(key))
        box.addStretch()
        self.output = QTextBrowser()
        self.output.setMinimumHeight(110)
        self.output.setMaximumHeight(160)
        self.output.setPlainText("Pronta. As permissões e ferramentas só mudam quando você usa os controles acima.")
        layout.addWidget(self.output)
        self.finished_job.connect(self.job_done)
        self.progress.connect(self.output.setPlainText)
        self.sync = QTimer(self)
        self.sync.setInterval(500)
        self.sync.timeout.connect(self.sync_permissions)
        self.sync.start()

    def button(self, layout, text, callback):
        button = QPushButton(text)
        button.clicked.connect(callback)
        layout.addWidget(button)
        return button

    def action_checkbox(self, layout, text, action):
        box = QCheckBox(text)
        box.setChecked(action.isChecked())
        box.setEnabled(action.isEnabled())
        box.toggled.connect(action.setChecked)
        layout.addWidget(box)
        return box

    def sync_permissions(self):
        for box, action in ((self.wake, self.controller.wake_action), (self.usb, self.controller.plug_action),
                            (self.plug_voice, self.controller.plug_voice)):
            box.blockSignals(True)
            box.setChecked(action.isChecked())
            box.blockSignals(False)

    def hide_companion(self):
        if not self.controller.tray_available:
            self.output.setPlainText("A bandeja não está disponível. Vou manter o chat acessível.")
            return
        self.controller.panel.hide()
        self.controller.window.hide()
        self.hide()

    def open_tool(self, name):
        try:
            launch_tool(self.root, name)
            self.output.setPlainText("Abri " + TOOLS[name][0] + ".")
        except (OSError, ValueError) as exc:
            self.output.setPlainText("Não consegui abrir: " + str(exc))

    def open_data(self):
        folder = self.root / "data"
        folder.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def set_startup(self, enabled):
        self.job(lambda: configure_shortcuts(self.root, enabled))

    def download_model(self, model):
        if self.running:
            return
        answer = QMessageBox.question(self, "Preparar modelo local",
            "Baixar/verificar " + model + " somente no Ollama local? "
            "O download pode consumir vários GB de internet e espaço. "
            "Não será utilizada API comercial nem cobrança por tokens. "
            "O Ollama precisa estar aberto. A escolha será usada ao reiniciar a Yuna.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if answer == QMessageBox.StandardButton.Yes:
            self.job(lambda: prepare_model(self.root, model, self.progress.emit))

    def job(self, action):
        if self.running:
            return
        self.running = True
        self.output.setPlainText("Preparando… Você pode continuar usando o chat.")
        def run():
            try:
                answer, success = action(), True
            except Exception as exc:
                answer, success = str(exc), False
            try:
                self.finished_job.emit(success, answer)
            except RuntimeError:
                pass
        Thread(target=run, name="Yuna-central", daemon=True).start()

    def job_done(self, success, message):
        self.running = False
        self.output.setPlainText(message if success else "Não foi possível concluir: " + message)
        if success:
            self.current_model_label.setText(
                "Modelo selecionado: " + load_selected_model(self.root)
                + " (reinicie a Yuna para aplicar)"
            )

    def closeEvent(self, event):
        self.hide()  # Mantém o progresso e as permissões ao reabrir a Central.
        event.ignore()
