"""Uma Central para recursos, permissões e manutenção da mesma Yuna."""
from pathlib import Path
from threading import Thread

from PySide6.QtCore import Qt, Signal, QUrl, QTimer
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QCheckBox, QDialog, QHBoxLayout, QLabel,
    QMessageBox, QPushButton, QScrollArea, QInputDialog, QTabWidget, QTextBrowser, QVBoxLayout, QWidget)

from app_tools import (TOOLS, RELEASE_URL, configure_shortcuts, installation_status,
                       launch_tool, prepare_model)
from self_model import VERSION
from model_config import MODEL_OPTIONS, LEGACY_OPTIONS, load_selected_model
from yuna_rag import (available_documents, index_document, search_documents,
                      clear_index, install_embedding_model)
from ollama_memory import loaded_models, loaded_model_status, unload_model
from windows_events import read_recent_events
from osv_security import check_package


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
        permissions, advanced = [QWidget() for _ in range(2)]
        home = QScrollArea()
        home.setWidgetResizable(True)
        home.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        home_content = QWidget()
        home.setWidget(home_content)
        maintenance = QScrollArea()
        maintenance.setWidgetResizable(True)
        maintenance.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        maintenance_content = QWidget()
        maintenance.setWidget(maintenance_content)
        integrations = QScrollArea()
        integrations.setWidgetResizable(True)
        integrations.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        integrations_content = QWidget()
        integrations.setWidget(integrations_content)
        for page, label in zip((home, permissions, maintenance, integrations, advanced),
                               ("Minha Yuna", "Permissões", "Preparação", "Integrações", "Avançado")):
            tabs.addTab(page, label)
        box = QVBoxLayout(home_content)
        self.button(box, "Conversar no chat compacto", controller.show_compact)
        self.button(box, "Abrir janela completa e documentos", controller.show_full)
        self.button(box, "Mostrar ou esconder a personagem 2D", controller.window.toggle_avatar)
        self.button(box, "Abrir avatar 3D", lambda: self.open_tool("3d"))
        self.button(box, "Conversar no navegador deste computador", lambda: self.open_tool("web"))
        self.button(box, "Recolher para segundo plano", self.hide_companion)
        modes_title = QLabel("Presença na bandeja • modo de funcionamento")
        modes_title.setStyleSheet("color:#cbb1ff;font-weight:700;")
        box.addWidget(modes_title)
        self.button(box, "● Ativa • conversar", lambda: controller.set_mode("ativa"))
        self.button(box, "◐ Econômica • reduzir verificações", lambda: controller.set_mode("economica"))
        self.button(box, "◇ Acompanhamento leve • USB/energia",
                    lambda: controller.set_mode("acompanhamento"))
        self.button(box, "Ⅱ Pausar • interromper atividades",
                    lambda: controller.set_mode("pausada"))
        mode_note = QLabel("Acompanhamento observa USB, energia, bateria e uso de RAM/disco "
            "deste PC. Não habilita câmera, microfone ou consultas automáticas à IA.")
        mode_note.setWordWrap(True)
        box.addWidget(mode_note)
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
        box = QVBoxLayout(maintenance_content)
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
        box = QVBoxLayout(integrations_content)
        intro = QLabel("Integrações opcionais: nada é consultado ou enviado sem você clicar. "
                       "Documentos ficam no computador; OSV recebe apenas pacote e versão.")
        intro.setWordWrap(True)
        box.addWidget(intro)
        label = QLabel("✦ Documentos e busca inteligente (RAG local)")
        label.setStyleSheet("color:#d5baff;font-weight:700;")
        box.addWidget(label)
        self.button(box, "Preparar EmbeddingGemma local (~622 MB)", self.rag_prepare)
        self.button(box, "Indexar documento já guardado na biblioteca", self.rag_index)
        self.button(box, "Pesquisar nos documentos indexados", self.rag_search)
        self.button(box, "Apagar somente índice semântico", self.rag_clear)
        label = QLabel("✦ Ollama • memória RAM/VRAM")
        label.setStyleSheet("color:#d5baff;font-weight:700;")
        box.addWidget(label)
        self.button(box, "Ver modelos carregados no Ollama", self.ollama_status)
        self.button(box, "Descarregar um modelo da memória (não desinstala)", self.ollama_unload)
        label = QLabel("✦ Diagnóstico local do Windows")
        label.setStyleSheet("color:#d5baff;font-weight:700;")
        box.addWidget(label)
        self.button(box, "Eventos do sistema • últimas 24 horas", lambda: self.win_events("System"))
        self.button(box, "Eventos de aplicativos • últimas 24 horas", lambda: self.win_events("Application"))
        label = QLabel("✦ Dependências • OSV.dev")
        label.setStyleSheet("color:#d5baff;font-weight:700;")
        box.addWidget(label)
        self.button(box, "Consultar vulnerabilidade de pacote PyPI / npm", self.osv_query)
        note = QLabel("A busca RAG não executa comandos nos documentos. "
                      "Descarregar modelo exige confirmação; ele permanece instalado. "
                      "Eventos do Windows são resumidos sem mensagens pessoais. "
                      "OSV requer internet e recebe apenas nome e versão informados.")
        note.setWordWrap(True)
        box.addWidget(note)
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
        self.controller.on_recolher()
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

    def rag_prepare(self):
        if self.running:
            return
        answer = QMessageBox.question(
            self, "Preparar busca semântica",
            "Baixar EmbeddingGemma (~622 MB) no Ollama LOCAL? "
            "Não usa API paga nem envia arquivos. O download usa internet.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if answer == QMessageBox.StandardButton.Yes:
            self.job(lambda: install_embedding_model(self.progress.emit))

    def rag_index(self):
        if self.running:
            return
        docs = available_documents(self.root)
        if not docs:
            self.output.setPlainText(
                "Guarde primeiro um arquivo na Biblioteca da janela completa da Yuna. "
                "Nenhuma pasta é varrida automaticamente.")
            return
        choices = [name + " [" + ident[:8] + "]" for ident, name in docs]
        selected, ok = QInputDialog.getItem(
            self, "Indexar biblioteca local", "Selecione o documento guardado:",
            choices, 0, False)
        if ok and selected:
            ident = docs[choices.index(selected)][0]
            answer = QMessageBox.question(
                self, "Autorizar indexação local",
                "Gerar embeddings deste documento no Ollama local e guardar "
                "os trechos em data/yuna_rag.sqlite? O arquivo não será enviado à nuvem.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if answer == QMessageBox.StandardButton.Yes:
                self.job(lambda: index_document(self.root, ident))

    def rag_search(self):
        if self.running:
            return
        question, ok = QInputDialog.getText(
            self, "Busca semântica", "Qual informação deseja encontrar?")
        if ok and question.strip():
            self.job(lambda: search_documents(self.root, question.strip()))

    def rag_clear(self):
        if self.running:
            return
        choice = QMessageBox.question(
            self, "Apagar índice local",
            "Apagar todas as representações e trechos da busca semântica? "
            "Isso NÃO apaga os documentos originais nem data/yuna.db.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if choice == QMessageBox.StandardButton.Yes:
            self.job(lambda: clear_index(self.root))

    def ollama_status(self):
        self.job(loaded_model_status)

    def ollama_unload(self):
        if self.running:
            return
        name, ok = QInputDialog.getText(
            self, "Liberar RAM/VRAM", "Nome exato do modelo carregado no Ollama "
            "(consulte Ver modelos carregados antes):")
        if not ok or not name.strip():
            return
        name = name.strip()
        choice = QMessageBox.question(
            self, "Confirmar liberação",
            "Pedir para o Ollama descarregar " + name + " da RAM/VRAM? "
            "Não desinstala nada e pode interromper outra conversa em andamento.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if choice == QMessageBox.StandardButton.Yes:
            self.job(lambda: unload_model(name))

    def win_events(self, category):
        self.job(lambda: read_recent_events(category))

    def osv_query(self):
        if self.running:
            return
        ecosystem, ok = QInputDialog.getItem(
            self, "Consulta OSV", "Ecossistema da dependência:",
            ["PyPI", "npm"], 0, False)
        if not ok:
            return
        package, ok = QInputDialog.getText(
            self, "Consulta OSV", "Nome público do pacote:")
        if not ok or not package.strip():
            return
        version, ok = QInputDialog.getText(
            self, "Consulta OSV", "Versão exata instalada (ex.: 3.1.4):")
        if ok and version.strip():
            self.job(lambda: check_package(ecosystem, package.strip(),
                                           version.strip()))

    def closeEvent(self, event):
        self.hide()  # Mantém o progresso e as permissões ao reabrir a Central.
        event.ignore()
