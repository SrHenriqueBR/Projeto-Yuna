"""Companhia na bandeja, chat compacto e comandos explícitos da interface desktop."""
import getpass
import hashlib
import html
import importlib.util
import os
import sys
from pathlib import Path
from threading import Event, Thread

from PySide6.QtCore import QObject, Qt, QTimer, Signal, QLockFile, QStandardPaths
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap, QAction
from PySide6.QtMultimedia import QMediaDevices
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel, QMenu,
    QMessageBox, QPlainTextEdit, QPushButton, QSystemTrayIcon, QTextBrowser,
    QVBoxLayout, QWidget, QFileDialog)

from companion_commands import BANKING_NOTICE, banking_action, game_intent, power_intent
from pc_controls import ShutdownCountdown
from plug_monitor import PlugMonitor
from plug_sense import describe_plugs, plug_intent
from tray_modes import MODES, mode_policy, should_observe, mode_tooltip
from health_watch import HealthGuidance, read_health, summary as health_summary


def app_icon(mode="ativa", microphone=False):
    """Y roxa com indicador de estado: funciona sem arquivo .ico externo."""
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#8062e8"))
    painter.drawEllipse(2, 2, 60, 60)
    painter.setPen(QColor("white"))
    font = painter.font()
    font.setPixelSize(36)
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "Y")
    # Ponto de status no canto inferior: azul apenas durante escuta autorizada.
    painter.setPen(QColor("#121526"))
    painter.setBrush(QColor("#4fa8ff") if microphone else
                     QColor(mode_policy(mode).color))
    painter.drawEllipse(44, 44, 18, 18)
    painter.end()
    return QIcon(pixmap)


class SingleInstance(QObject):
    activated = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        identity = os.environ.get("USERDOMAIN", "") + getpass.getuser() + str(Path.home())
        self.name = "YunaApp-" + hashlib.sha256(identity.encode()).hexdigest()[:20]
        self.lock = QLockFile(str(Path(QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.TempLocation)) / (self.name + ".lock")))
        self.server = QLocalServer(self)
        self.server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
        self.server.newConnection.connect(self._activate)

    def acquire(self):
        if not self.lock.tryLock(100):
            socket = QLocalSocket()
            socket.connectToServer(self.name)
            if not socket.waitForConnected(1500):
                raise RuntimeError("A Yuna já está iniciando ou a trava está indisponível. Aguarde e tente abrir novamente.")
            socket.disconnectFromServer()
            return False
        QLocalServer.removeServer(self.name)  # só depois de possuir a trava desta conta
        if not self.server.listen(self.name):
            self.lock.unlock()
            raise RuntimeError("Não consegui iniciar o canal local da Yuna.")
        return True

    def _activate(self):
        while self.server.hasPendingConnections():
            socket = self.server.nextPendingConnection()
            socket.disconnectFromServer()
            socket.deleteLater()
        self.activated.emit()  # nenhum conteúdo recebido é interpretado como comando

    def close(self):
        self.server.close()
        self.lock.unlock()


class CompactInput(QPlainTextEdit):
    submitted = Signal()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not (
                event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            self.submitted.emit()
            event.accept()
            return
        super().keyPressEvent(event)


class CompactChat(QWidget):
    submitted = Signal(str)

    def __init__(self, controller):
        super().__init__(None, Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        self.controller = controller
        self.setWindowTitle("Yuna.app • Chat compacto")
        self.setWindowIcon(app_icon())
        self.resize(460, 420)
        self.setMinimumSize(340, 280)
        self.setStyleSheet("""
            QWidget { background:#111116; color:#f3f3fa; font-family:'Segoe UI'; font-size:13px; }
            QLabel#brand { font-size:18px; font-weight:600; }
            QLabel#status { color:#b4b4c5; font-size:11px; }
            QTextBrowser { background:#111116; border:0; padding:4px; }
            QFrame#input { background:#24242b; border:1px solid #3b3b45; border-radius:24px; }
            QPlainTextEdit { background:transparent; border:0; padding:8px; }
            QPushButton { background:#24242b; border:0; border-radius:14px; padding:8px; }
            QPushButton:hover { background:#393943; }
            QPushButton#send { background:#426fe3; font-size:18px; border-radius:20px; }
            QPushButton:disabled { color:#686875; background:#25252b; }
            QMenu { background:#202027; padding:5px; }
            QMenu::item { padding:8px 15px; }
            QMenu::item:selected { background:#403856; }
            QScrollBar:vertical { background:transparent; width:6px; margin:0; }
            QScrollBar::handle:vertical { background:#55515e; border-radius:3px; min-height:24px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background:transparent; }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 14)
        top = QHBoxLayout()
        brand = QLabel("✦  Yuna.app")
        brand.setObjectName("brand")
        top.addWidget(brand, 1)
        self.more = QPushButton("•••")
        self.more.setToolTip("Voz, jogos, câmera e segundo plano")
        top.addWidget(self.more)
        expand = QPushButton("↗")
        expand.setToolTip("Abrir janela completa")
        expand.clicked.connect(controller.show_full)
        top.addWidget(expand)
        layout.addLayout(top)
        self.state = QLabel("Pronta quando você quiser.")
        self.state.setObjectName("status")
        self.state.setWordWrap(True)
        layout.addWidget(self.state)
        self.messages = QTextBrowser()
        self.messages.setOpenLinks(False)
        self.messages.setOpenExternalLinks(False)
        self.messages.document().setMaximumBlockCount(300)
        layout.addWidget(self.messages, 1)
        self.power_notice = QPushButton()
        self.power_notice.setStyleSheet("background:#663341;color:white;padding:10px;border-radius:9px")
        self.power_notice.clicked.connect(controller.cancel_shutdown)
        self.power_notice.hide()
        layout.addWidget(self.power_notice)
        frame = QFrame()
        frame.setObjectName("input")
        row = QHBoxLayout(frame)
        row.setContentsMargins(7, 3, 8, 3)
        self.input = CompactInput()
        self.input.setPlaceholderText("Converse com a Yuna…")
        self.input.setFixedHeight(58)
        row.addWidget(self.input, 1)
        self.mic = QPushButton("🎙")
        self.mic.setToolTip("Ditar uma mensagem (local)")
        self.mic.clicked.connect(controller.window.request_microphone)
        row.addWidget(self.mic)
        self.send = QPushButton("↑")
        self.send.setObjectName("send")
        self.send.setFixedSize(40, 40)
        self.send.setToolTip("Enviar mensagem")
        self.send.clicked.connect(self.submit)
        self.input.submitted.connect(self.submit)
        row.addWidget(self.send)
        layout.addWidget(frame)
        bottom = QHBoxLayout()
        self.listening = QLabel("Microfone contínuo desligado")
        self.listening.setObjectName("status")
        bottom.addWidget(self.listening, 1)
        stop = QPushButton("■ Parar")
        stop.clicked.connect(controller.window.emergency_stop)
        bottom.addWidget(stop)
        layout.addLayout(bottom)
        self._placed = False

    def submit(self):
        text = self.input.toPlainText().strip()
        if text:
            self.submitted.emit(text)

    def add_message(self, author, text):
        color = "#acbfff" if author in ("Você", "Kaizen") else "#c6adff"
        safe = html.escape(str(text)[:16000]).replace("\n", "<br>")
        self.messages.append(f'<p style="margin-top:12px;color:{color}"><b>{html.escape(author)}</b></p>'
                             f'<p style="color:#eeeeF6;margin-bottom:12px">{safe}</p>')
        bar = self.messages.verticalScrollBar()
        bar.setValue(bar.maximum())

    def show_panel(self):
        if not self._placed:
            area = self.screen().availableGeometry()
            self.resize(min(self.width(), area.width()), min(self.height(), area.height()))
            self.move(max(area.left(), area.right() - self.width() - 18),
                      max(area.top(), area.bottom() - self.height() - 18))
            self._placed = True
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):
        if self.controller.tray_available:
            self.hide()
            self.controller.on_recolher()
            event.ignore()
        else:
            event.accept()
            self.controller.show_full()


class CompanionController(QObject):
    wake_heard = Signal(int, str)
    wake_failed = Signal(int, str)
    wake_ready = Signal(int)
    game_done = Signal(int, str)

    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.closing = False
        self.mode = "ativa"
        self._background_start = False
        self.wake = None
        self.wake_generation = 0
        self._wake_live = False
        self.wake_paused = Event()
        self.game_stop = Event()
        self.game_generation = 0
        self.game_pending = False
        self.shutdown = ShutdownCountdown()
        self.audio_missing = None
        self.center = None
        self.plugs = PlugMonitor(self)
        self.health = HealthGuidance()
        self.plugs.notice.connect(self.connection_notice)
        self.plugs.power_changed.connect(window.poll_battery)
        self.panel = CompactChat(self)
        self.panel.submitted.connect(self.submit)
        self.menu = QMenu(self.panel)
        self.status_action = QAction("● Yuna ativa • pronta para conversar", self.menu)
        self.status_action.setEnabled(False)
        self.menu.addAction(self.status_action)
        self.modes_menu = self.menu.addMenu("Modo de funcionamento")
        self.mode_actions = {}
        for key, title in (("ativa", "● Ativa • conversar"),
                           ("economica", "◐ Econômica • menor consumo"),
                           ("acompanhamento", "◇ Acompanhamento leve • USB/energia"),
                           ("pausada", "Ⅱ Pausar • interromper atividades")):
            action = QAction(title, self.modes_menu)
            action.setCheckable(True)
            action.setChecked(key == self.mode)
            action.triggered.connect(
                lambda _checked=False, selected=key: self.set_mode(selected))
            self.modes_menu.addAction(action)
            self.mode_actions[key] = action
        self.menu.addSeparator()
        self.menu.addAction("Central da Yuna…", self.show_center)
        self.menu.addAction("Abrir chat compacto", self.show_compact)
        self.menu.addAction("Abrir janela completa", self.show_full)
        self.wake_action = QAction('Escutar “Olá Yuna” nesta sessão', self.menu)
        self.wake_action.setCheckable(True)
        self.wake_action.toggled.connect(self.toggle_wake)
        self.menu.addAction(self.wake_action)
        self.plug_action = QAction("Perceber USB e energia", self.menu)
        self.plug_action.setCheckable(True)
        self.plug_action.setChecked(sys.platform == "win32")
        self.plug_action.setEnabled(sys.platform == "win32")
        self.plug_action.toggled.connect(self.toggle_plugs)
        self.menu.addAction(self.plug_action)
        self.plug_voice = QAction("Falar avisos de conexões nesta sessão", self.menu)
        self.plug_voice.setCheckable(True)
        self.menu.addAction(self.plug_voice)
        self.menu.addAction("Conexões do computador…", self.show_connections)
        self.menu.addAction("Configurar controle de jogo…", self.configure_game)
        self.menu.addAction("Abrir câmera…", window.open_camera_viewer)
        self.menu.addAction("Saúde deste PC (RAM/disco)…", self.show_health)
        self.menu.addAction("Diagnóstico do computador", lambda: self.submit("/diagnostico"))
        self.menu.addSeparator()
        self.menu.addAction("Cancelar desligamento", self.cancel_shutdown)
        self.menu.addAction("Parar ações e microfone", window.emergency_stop)
        self.menu.addAction("Sair da Yuna", self.quit)
        self.panel.more.setMenu(self.menu)
        self.tray = QSystemTrayIcon(app_icon(), self)
        self.tray.setToolTip(mode_tooltip(self.mode))
        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(lambda reason: self.show_compact()
            if reason in (QSystemTrayIcon.ActivationReason.Trigger,
                          QSystemTrayIcon.ActivationReason.DoubleClick) else None)
        self.tray_available = QSystemTrayIcon.isSystemTrayAvailable()
        if self.tray_available:
            self.tray.show()
        self.devices = QMediaDevices(self)
        self.devices.audioInputsChanged.connect(self.check_audio)
        self.devices.audioOutputsChanged.connect(self.check_audio)
        self.wake_heard.connect(self._heard)
        self.wake_failed.connect(self._wake_error)
        self.wake_ready.connect(self._wake_ready)
        self.game_done.connect(self._game_done)
        self.timer = QTimer(self)
        self.timer.setInterval(200)
        self.timer.timeout.connect(self.tick)
        self.timer.start()
        self.health_timer = QTimer(self)
        self.health_timer.setInterval(300000)
        self.health_timer.timeout.connect(self._health_tick)
        self._update_tray_indicator()

    def _update_tray_indicator(self):
        """Apenas informações locais; não consulta serviços nem faz inferência."""
        plugged = bool(self.plugs.active)
        listening = bool(self._wake_live and self.wake_action.isChecked()
                         and self.mode == "ativa")
        self.tray.setIcon(app_icon(self.mode, microphone=listening))
        self.tray.setToolTip(mode_tooltip(
            self.mode, microphone=listening, usb=plugged))
        self.status_action.setText(
            "● Yuna " + mode_policy(self.mode).title + " • " +
            ("escuta autorizada" if listening else
             "USB/energia acompanhados" if plugged else "em espera"))
        for key, action in self.mode_actions.items():
            action.setChecked(key == self.mode)
        self.plug_action.setText(
            "Perceber USB e energia" +
            (" (suspenso neste modo)" if self.plug_action.isChecked()
             and not mode_policy(self.mode).usb_events else ""))

    def _quiet_optional_visuals(self):
        """Reduz renderização sem reabrir câmera/microfone ao despertar."""
        avatar = self.window.avatar_window
        if avatar is not None and avatar.isVisible():
            avatar.hide()
            self.window.avatar_button.setText("✦  Mostrar Yuna viva")
        if self.window.avatar_bridge is not None:
            self.window.avatar_bridge.stop()
            self.window.avatar_bridge = None
            self.window.avatar3d_button.setText("◇  Conectar Yuna 3D")
        if self.window.unreal_bridge is not None:
            self.window.unreal_bridge.stop()
            self.window.unreal_bridge = None
            self.window.unreal_button.setText("◇  Conectar Yuna Unreal")

    def set_mode(self, mode):
        """Modo manual não liga escuta/câmera. Pausa interrompe ações pendentes."""
        policy = mode_policy(mode)
        if self.closing:
            return
        previous = self.mode
        self.mode = mode
        if mode == "acompanhamento" and not self.plug_action.isChecked() and sys.platform == "win32":
            # Escolher explicitamente este modo concede apenas USB/energia.
            self.plug_action.setChecked(True)
        if mode == "acompanhamento":
            if previous != mode:
                self.health.reset()
            self.health_timer.start()
            if previous != mode:
                QTimer.singleShot(2500, self._health_tick)
        else:
            self.health_timer.stop()
        if mode != "ativa" and self.wake_action.isChecked():
            self.wake_action.setChecked(False)
        if mode == "pausada" and previous != "pausada":
            self.window.emergency_stop()
        if mode in ("economica", "pausada"):
            self._quiet_optional_visuals()
        self.toggle_plugs(self.plug_action.isChecked())
        if mode != "ativa" and self.plug_voice.isChecked():
            self.plug_voice.setChecked(False)
        if self.window.battery_timer is not None:
            if policy.battery_ms is None:
                self.window.battery_timer.stop()
            else:
                self.window.battery_timer.setInterval(policy.battery_ms)
                if not self.window.battery_timer.isActive():
                    self.window.battery_timer.start()
        if self.window.unreal_heartbeat is not None:
            if policy.unreal_heartbeat:
                if not self.window.unreal_heartbeat.isActive():
                    self.window.unreal_heartbeat.start()
            else:
                self.window.unreal_heartbeat.stop()
        self.timer.setInterval(policy.timer_ms)
        self._update_tray_indicator()
        self.panel.state.setText(policy.detail)
        self.window.status.setText("Yuna • " + policy.title)
        if self.window.hero_timer is not None and mode != "ativa":
            self.window.hero_timer.stop()
        elif self.window.hero_timer is not None and self.window.isVisible():
            self.window.hero_timer.start()

    def on_recolher(self):
        """Fechar minimiza para um ícone leve, sem encerrar a aplicação."""
        if self.tray_available and self.mode == "ativa":
            self.set_mode("economica")

    def start(self, background=False, compact=False):
        self._background_start = bool(background and self.tray_available)
        self.set_mode("economica" if self._background_start else "ativa")
        if compact:
            self.show_compact()
        elif background and self.tray_available:
            self.window.hide()
        else:
            self.show_full()
        self.check_audio()

    def show_center(self):
        if self.closing:
            return
        if self.center is None:
            from app_center import YunaCenter
            from yuna import ROOT
            self.center = YunaCenter(self, ROOT)
        self.center.show()
        self.center.raise_()
        self.center.activateWindow()

    def toggle_plugs(self, enabled):
        if not self.closing and should_observe(
                self.mode, windows=sys.platform == "win32", permission=enabled):
            self.window.winId()  # Cria HWND mesmo com a janela recolhida na bandeja.
            self.plugs.start()
        else:
            self.plugs.stop()
        self._update_tray_indicator()

    def _health_tick(self):
        """Acompanhamento agregado, no máximo a cada 5 min; jamais usa Ollama."""
        if self.closing or self.mode != "acompanhamento":
            return
        for message in self.health.observe(read_health()):
            self.window.add_message("Yuna", message)
            if (self.tray_available and not self.window.isVisible()
                    and not self.panel.isVisible()):
                self.tray.showMessage("Yuna • saúde do PC", message,
                    QSystemTrayIcon.MessageIcon.Information, 5000)

    def show_health(self):
        """Verificação manual explícita, disponível mesmo no modo econômico."""
        QMessageBox.information(
            self.panel, "Yuna • saúde do computador",
            health_summary(read_health()))

    def connection_status(self):
        if sys.platform != "win32":
            return "A percepção de USB e energia desta versão está disponível no Windows."
        if not self.plugs.active:
            if not mode_policy(self.mode).usb_events:
                return ("A percepção de USB/energia está suspensa no modo " +
                        mode_policy(self.mode).title +
                        ". Mude para Ativa ou Acompanhamento leve na bandeja.")
            return "A percepção está desligada. Marque Perceber USB e energia no menu •••."
        self.plugs.request_refresh()
        return describe_plugs(self.plugs.snapshot)

    def show_connections(self):
        QMessageBox.information(self.panel, "Yuna • conexões", self.connection_status())

    def connection_notice(self, message):
        if self.closing or not self.plugs.active or self.mode not in ("ativa", "acompanhamento"):
            return
        # Avisos efêmeros: não viram comandos, prompts, fatos ou inventário persistente.
        self.window.add_message("Yuna", message)
        if self.tray_available and not self.window.isVisible() and not self.panel.isVisible():
            self.tray.showMessage("Yuna • conexões", message,
                                  QSystemTrayIcon.MessageIcon.Information, 4000)
        if (self.plug_voice.isChecked() and not self.window.voice_busy
                and not self.window.microphone_busy and self.window.send_button.isEnabled()):
            self.say_connection(message)

    def say_connection(self, message):
        # A voz Edge opcional é externa: nomes/status reais só vão à voz Windows.
        self.window.say("Confira as conexões do computador no chat."
                        if self.window.voice_index == 2 else message)

    def show_compact(self):
        if self.closing:
            return
        if self.mode == "pausada":
            self.set_mode("ativa")
        self._background_start = False
        self.window.hide()
        self.panel.show_panel()

    def show_full(self):
        if self.closing:
            return
        self._background_start = False
        if self.mode in ("pausada", "economica"):
            self.set_mode("ativa")
        self.panel.hide()
        self.window.showNormal()
        self.window.raise_()
        self.window.activateWindow()

    def check_audio(self):
        if self.closing:
            return
        input_ok = bool(QMediaDevices.audioInputs()) and not QMediaDevices.defaultAudioInput().isNull()
        output_ok = bool(QMediaDevices.audioOutputs()) and not QMediaDevices.defaultAudioOutput().isNull()
        packages = all(importlib.util.find_spec(name) for name in ("sounddevice", "faster_whisper"))
        missing = not (input_ok and output_ok and packages)
        if output_ok:
            self.window.audio_output.setDevice(QMediaDevices.defaultAudioOutput())
        if missing and missing != self.audio_missing:
            reason = "Sem microfone disponível" if not input_ok else (
                "Sem saída de áudio disponível" if not output_ok else "Ditado local ainda não instalado")
            self.panel.state.setText(reason + " • podemos conversar por texto.")
            if self.mode == "ativa" and not self._background_start:
                self.show_compact()
        if not input_ok and self.wake_action.isChecked():
            self.wake_action.setChecked(False)
        self.audio_missing = missing

    def submit(self, text):
        from emergency_stop import is_stop_request
        # Paradas e cancelamento continuam acessíveis enquanto o modelo pensa.
        urgent = is_stop_request(text) or power_intent(text) == "cancel" or game_intent(text) == "stop"
        if not self.window.composer.isEnabled() and not urgent:
            self.panel.state.setText("Estou respondendo. Use Parar para interromper antes de outro pedido.")
            return
        self.panel.input.clear()
        self.window.composer.setPlainText(text)
        self.window.send_message()

    def reply(self, request, answer, speak=True):
        self.window.add_message("Você", request)
        self.window.add_message("Yuna", answer)
        self.window.worker.record(request, answer)
        if speak:
            self.window.say(answer)

    def handle(self, text):
        if plug_intent(text):
            self.window.add_message("Você", text)
            answer = self.connection_status()
            self.window.add_message("Yuna", answer)
            self.say_connection(answer)
            return True
        if banking_action(text):
            self.reply(text, BANKING_NOTICE)
            return True
        from wake_schedule import wake_intent
        wake = wake_intent(text)
        if wake:
            action, when = wake
            if action == "agendar":
                answer = QMessageBox.question(self.panel, "Despertar da suspensão",
                    f"Agendar para {when:%d/%m/%Y às %H:%M}, no horário deste PC?\n\n"
                    "A Yuna pode solicitar ao Windows que desperte da suspensão/hibernação se o hardware permitir. "
                    "Mantenha sua sessão conectada e o computador na tomada. Não liga um PC totalmente desligado; isso exige configuração compatível na BIOS. "
                    "Este horário substitui o despertar anterior da Yuna.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
                if answer != QMessageBox.StandardButton.Yes:
                    return True
            self.window.add_message("Você", text)
            self.window.set_busy(True)
            self.window.worker.queue.put(("wake", text, action, when))
            return True
        intent = power_intent(text)
        if intent == "cancel":
            self.cancel_shutdown()
            return True
        if intent == "shutdown":
            if os.name != "nt":
                self.reply(text, "O desligamento exige Windows.")
            else:
                self.window.player.stop()
                self.window.voice_busy = False
                self.window._speech_generation += 1
                self.window._speech_queue.clear()
                self.shutdown.start()
                self.show_compact()
                self.reply(text, "Sim, Kaizen. Desligarei o computador em 30 segundos. "
                           "Boa noite, zzzzz! Salve seu trabalho. Para cancelar, clique no aviso ou diga: Yuna, cancele o desligamento.")
                self.tick()
            return True
        action = game_intent(text)
        if action == "configure":
            self.configure_game()
        elif action == "stop":
            self.stop_game()
            self.reply(text, "Encerrei o controle do jogo.")
        elif action:
            self.queue_game(text, action)
        else:
            return False
        return True

    def cancel_shutdown(self):
        existed = self.shutdown.cancel()
        self.panel.power_notice.hide()
        self.reply("Cancelar desligamento", "Cancelei o desligamento da Yuna." if existed
                   else "Não há desligamento pendente na Yuna.")

    def tick(self):
        paused = self.window.voice_busy or self.window.microphone_busy or not self.window.composer.isEnabled()
        self.wake_paused.set() if paused else self.wake_paused.clear()
        remaining = self.shutdown.remaining()
        if remaining is not None:
            self.panel.power_notice.setText(f"Desligamento em {remaining}s  ·  Cancelar")
            self.panel.power_notice.show()
            try:
                if self.shutdown.tick():
                    self.panel.power_notice.hide()
                    self.window.add_message("Yuna", "Solicitei o desligamento ao Windows. Aplicativos com trabalho aberto podem impedi-lo.")
            except Exception as exc:
                self.panel.power_notice.hide()
                self.window.show_error(str(exc))

    def toggle_wake(self, enabled):
        if enabled and self.mode != "ativa" and not self.closing:
            self.set_mode("ativa")  # pedido explícito de escuta sai da economia
        self.wake_generation += 1
        generation = self.wake_generation
        if enabled and self.wake is not None and self.wake.is_alive():
            self.wake_action.setChecked(False)
            self.panel.state.setText("A escuta anterior está terminando. Aguarde antes de reativar.")
            return
        if self.wake is not None:
            self.wake.stop()
        self._wake_live = False
        self.panel.listening.setText("Microfone contínuo desligado")
        self._update_tray_indicator()
        if not enabled:
            return
        if not all(importlib.util.find_spec(name) for name in ("sounddevice", "faster_whisper")):
            QMessageBox.information(self.panel, "Voz local", "Prepare a cópia pelo Yuna.bat ou use Central da Yuna → Preparação → Atualizar ou reparar o app. O chat por texto continua disponível.")
            self.wake_action.setChecked(False)
            return
        answer = QMessageBox.question(self.panel, "Escuta local nesta sessão",
            "O microfone ficará ligado para reconhecer chamadas que começam com “Yuna”, “Olá Yuna” ou “Oi Yuna”. "
            "Não é reconhecimento exclusivo da sua voz: outra pessoa ou um áudio próximo também pode chamar. "
            "O Whisper processa o áudio localmente; não guardo gravações. Na primeira ativação pode baixar o modelo base. "
            "Use Parar ou desmarque esta opção para desligar. Ativar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            self.wake_action.setChecked(False)
            return
        from wake_listener import WakeListener
        self.panel.listening.setText("Preparando escuta local…")
        self.wake = WakeListener(
            lambda text: self.wake_heard.emit(generation, text),
            lambda error: self.wake_failed.emit(generation, error),
            lambda: self.wake_ready.emit(generation), self.wake_paused)
        self.wake.start()

    def _wake_ready(self, generation):
        if generation == self.wake_generation and not self.closing:
            self._wake_live = True
            self.panel.listening.setText('● Microfone ativo • diga “Olá Yuna”')
            self._update_tray_indicator()

    def _heard(self, generation, text):
        if generation == self.wake_generation and not self.closing:
            self.submit(text)

    def _wake_error(self, generation, error):
        if generation == self.wake_generation and not self.closing:
            self.wake_action.setChecked(False)
            self.show_compact()
            self.panel.state.setText(error)

    def configure_game(self):
        if os.name != "nt":
            self.window.show_error("Controle de jogos disponível somente no Windows.")
            return
        filename, _ = QFileDialog.getOpenFileName(self.panel, "Escolha o executável do jogo", "", "Jogo Windows (*.exe)")
        if not filename:
            return
        try:
            from game_controls import allowed_game
            game = allowed_game(filename)
            if not Path(filename).is_file():
                raise ValueError("Selecione um executável existente.")
            answer = QMessageBox.question(self.panel, "Controle deste jogo por 5 minutos",
                "Autorizar comandos curtos nesta sessão individual/offline?\n\n"
                "WASD: mover • Espaço: pular • E: interagir • C: agachar • Esc: pausa • setas: olhar.\n"
                "Os atalhos precisam corresponder aos controles do jogo. Cada comando espera 3 segundos para você voltar ao jogo. "
                "A Yuna não joga sozinha. Até 120 ações; Parar revoga a sessão.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if answer != QMessageBox.StandardButton.Yes:
                return
            self.stop_game()
            self.window.game_session.authorize(game, approved=True, single_player=True)
            self.reply("Configurar controle de jogo", "Controle autorizado por 5 minutos. Experimente “Yuna, no jogo pule”. Volte ao jogo durante a contagem de 3 segundos.")
        except Exception as exc:
            self.window.show_error(str(exc))

    def stop_game(self):
        self.game_generation += 1
        self.game_stop.set()
        self.window.game_session.stop()
        self.game_pending = False

    def queue_game(self, text, action):
        if not self.window.game_session.active:
            self.reply(text, "Escolha primeiro Configurar controle de jogo no menu da Yuna.")
            return
        if self.game_pending:
            self.reply(text, "Já há uma ação de jogo aguardando. Use Parar para cancelar.", speak=False)
            return
        self.game_pending = True
        token = Event()
        self.game_stop = token
        generation = self.game_generation
        self.reply(text, "Volte ao jogo autorizado: enviarei o comando em 3 segundos.", speak=False)
        def launch():
            if generation != self.game_generation or token.is_set() or self.closing:
                return
            def work():
                try:
                    from game_controls import execute_action
                    result = execute_action(self.window.game_session, action, token.is_set)
                except Exception as exc:
                    result = str(exc)
                self.game_done.emit(generation, result)
            Thread(target=work, daemon=True, name="YunaGameCommand").start()
        QTimer.singleShot(3000, launch)

    def _game_done(self, generation, message):
        if generation == self.game_generation and not self.closing:
            self.game_pending = False
            self.window.add_message("Yuna", message)
            self.window.worker.record("Resultado do comando de jogo", message)

    def stop(self):
        self.plug_voice.setChecked(False)
        self.stop_game()
        self.shutdown.cancel()
        self.panel.power_notice.hide()
        self.wake_action.setChecked(False)

    def quit(self):
        self.closing = True
        self.health_timer.stop()
        self.plugs.stop()
        self.stop()
        self.timer.stop()
        self.panel.hide()
        self.tray.hide()
        self.window.close()
        QApplication.instance().quit()

    def cleanup(self):
        self.closing = True
        self.health_timer.stop()
        if self.center is not None:
            self.center.hide()
            self.center.sync.stop()
        self.plugs.stop()
        self.stop()
        self.timer.stop()
        self.panel.hide()
        self.panel.deleteLater()
        self.tray.hide()
