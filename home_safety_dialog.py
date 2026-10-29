"""Modo Segurança visível e temporário — SOS e medidor de som local.

Nenhuma captura começa ao instalar/abrir a Yuna. Quem usa este notebook
ativa por até 30 minutos. Não grava áudio, não transcreve, não identifica
pessoas e não transmite amostras de microfone. WhatsApp permanece manual;
Telegram é opcional e envia SOMENTE descrições fixas de eventos.
"""
import math
import struct
import time
import threading
from urllib.parse import quote

from PySide6.QtCore import QObject, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QShortcut, QKeySequence
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QVBoxLayout,
)

from home_safety import (
    AlertPending, SafetySession, SoundLevelDetector, SAFETY_EVENTS,
    validate_contact,
)
from free_alert_budget import AlertBudget
from free_telegram_alerts import (
    FreeTelegramNotifier, TelegramConfigurationError, TelegramSendError
)


class _TelegramResults(QObject):
    completed = Signal(int, bool)



def rms_pcm16le(pcm):
    """Nível de volume do bloco de áudio; descarta imediatamente o conteúdo."""
    if not isinstance(pcm, bytes) or len(pcm) < 2:
        return 0.0
    size = len(pcm) // 2
    if size == 0:
        return 0.0
    energy = sum(v * v for (v,) in struct.iter_unpack(
        "<h", pcm[:size * 2]
    ))
    return min(1.0, math.sqrt(energy / size) / 32768)


def whatsapp_draft_url(contact, kind):
    """Cria somente um rascunho. Não transmite evento nem envia a mensagem."""
    if kind not in SAFETY_EVENTS:
        raise ValueError("Alerta não reconhecido")
    number = validate_contact(contact)
    text = (
        "Yuna • Alerta doméstico: " + SAFETY_EVENTS[kind].text +
        ". Verifique por ligação ou mensagem. "
        "Este aviso não comprova uma emergência."
    )
    return "https://wa.me/" + number + "?text=" + quote(text, safe="")


class HomeSafetyDialog(QDialog):
    state_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._session = SafetySession()
        self._pending = AlertPending()
        self._detector = SoundLevelDetector()
        self._audio = None
        self._device = None
        self._audio_mode = False
        self._telegram_notifier = None
        self._alert_budget = AlertBudget()
        self._notification_epoch = 0
        self._cancel_send = threading.Event()
        self._telegram_signals = _TelegramResults(self)
        self._telegram_signals.completed.connect(self._on_telegram_result)
        self.setWindowTitle("Yuna • Segurança doméstica DESLIGADA")
        self.resize(565, 560)
        self.setMinimumSize(475, 495)
        self.setStyleSheet(
            "QDialog{background:#171324;color:#eee9f6;}"
            "QLineEdit{background:#29223c;color:white;padding:10px;"
            "border:1px solid #675581;border-radius:8px;}"
            "QPushButton{padding:10px;background:#5a467d;color:white;"
            "border-radius:8px;}"
            "QCheckBox{color:#e7dff5;}"
        )
        content = QVBoxLayout(self)
        self.state = QLabel("DESLIGADO — nenhuma captura ativa")
        self.state.setStyleSheet("font-weight:bold;color:#d6b9f5;")
        content.addWidget(self.state)
        desc = QLabel(
            "Este modo precisa ser ativado pela pessoa no notebook. "
            "O SOS abre um rascunho manual de WhatsApp; você também pode "
            "ativar avisos gratuitos automáticos por Telegram. O microfone "
            "é opcional e detecta apenas volume alto — não reconhece "
            "pedidos de ajuda nem identifica ameaças."
        )
        desc.setWordWrap(True)
        content.addWidget(desc)
        content.addWidget(QLabel("Contato WhatsApp de confiança (DDI e DDD):"))
        self.recipient = QLineEdit()
        self.recipient.setPlaceholderText("Exemplo: 5534999999999")
        self.recipient.setMaxLength(20)
        content.addWidget(self.recipient)
        self.sound_checkbox = QCheckBox(
            "Permitir medição local de sons altos por até 30 minutos"
        )
        self.sound_checkbox.setChecked(False)
        content.addWidget(self.sound_checkbox)
        self.telegram_checkbox = QCheckBox(
            "Telegram gratuito: enviar SOS/som alto automaticamente (opcional)"
        )
        self.telegram_checkbox.setChecked(False)
        self.telegram_checkbox.toggled.connect(self._update_telegram_form)
        content.addWidget(self.telegram_checkbox)
        self.telegram_bot_token = QLineEdit()
        self.telegram_bot_token.setPlaceholderText(
            "Token do bot (BotFather) — não será salvo"
        )
        self.telegram_bot_token.setEchoMode(QLineEdit.EchoMode.Password)
        self.telegram_bot_token.setMaxLength(128)
        self.telegram_bot_token.setEnabled(False)
        content.addWidget(self.telegram_bot_token)
        self.telegram_chat_id = QLineEdit()
        self.telegram_chat_id.setPlaceholderText(
            "ID numérico da conversa privada com o bot"
        )
        self.telegram_chat_id.setMaxLength(20)
        self.telegram_chat_id.setEnabled(False)
        content.addWidget(self.telegram_chat_id)
        self.telegram_help = QLabel(
            "O Telegram é um serviço externo. Envia somente o tipo de "
            "alerta, nunca áudio, imagem ou transcrição. Máximo 6 "
            "tentativas por sessão; sem mensagens pagas. "
            "Para configurar, veja docs/ALERTAS_GRATUITOS_YUNA.md"
        )
        self.telegram_help.setWordWrap(True)
        content.addWidget(self.telegram_help)
        self.activate = QPushButton("Ativar modo Segurança (30 min)")
        self.activate.clicked.connect(self.activate_safety)
        content.addWidget(self.activate)
        self.sos = QPushButton("SOS — Preparar mensagem de ajuda")
        self.sos.clicked.connect(self.send_sos_draft)
        self.sos.setEnabled(False)
        content.addWidget(self.sos)
        self.warning = QLabel("")
        self.warning.setWordWrap(True)
        self.warning.setStyleSheet("color:#f3ba9b;")
        content.addWidget(self.warning)
        self.cancel_warning = QPushButton("Cancelar alerta de som (falso alarme)")
        self.cancel_warning.clicked.connect(self.cancel_sound_alert)
        self.cancel_warning.setVisible(False)
        content.addWidget(self.cancel_warning)
        actions = QHBoxLayout()
        self.stop_button = QPushButton("■ Desligar monitoramento")
        self.stop_button.clicked.connect(self.stop_safety)
        actions.addWidget(self.stop_button)
        content.addLayout(actions)
        content.addStretch(1)

        self.tick = QTimer(self)
        self.tick.setInterval(1000)
        self.tick.timeout.connect(self._tick)
        self.shortcut = QShortcut(QKeySequence("Ctrl+Shift+X"), self)
        self.shortcut.activated.connect(self.stop_safety)

    @property
    def active(self):
        return self._session.active

    def _update_telegram_form(self, enabled):
        if not self.active:
            self.telegram_bot_token.setEnabled(enabled)
            self.telegram_chat_id.setEnabled(enabled)

    def activate_safety(self):
        if self.active:
            return
        try:
            contact = validate_contact(self.recipient.text())
        except ValueError:
            self.warning.setText("Informe um número WhatsApp válido com DDI e DDD.")
            return
        microphone = self.sound_checkbox.isChecked()
        notifier = None
        if self.telegram_checkbox.isChecked():
            try:
                notifier = FreeTelegramNotifier(
                    self.telegram_bot_token.text(),
                    self.telegram_chat_id.text(),
                )
            except TelegramConfigurationError:
                self.warning.setText(
                    "Configure o bot e o ID numérico da conversa privada "
                    "do Telegram; não compartilhe o token."
                )
                return
        decision = QMessageBox.question(
            self, "Autorização local de segurança",
            "A pessoa que está usando este notebook concorda em ativar "
            "por até 30 minutos o botão SOS" +
            (" e a medição LOCAL de volume pelo microfone" if microphone else "") +
            "?\n\nNenhum áudio, imagem ou conversa será armazenado ou "
            "enviado. Sons altos podem causar falsos alertas. "
            "O WhatsApp abrirá um rascunho e dependerá de alguém "
            "pressionar Enviar." +
            ("\\n\\nSe escolher Telegram, eventos SOS/som alto serão "
             "enviados automaticamente como texto para o ID informado, "
             "por um serviço EXTERNO gratuito (no uso normal). "
             "Não são enviadas imagens, áudio nem conversas."
             if notifier else
             "\\n\\nO Telegram automático está DESLIGADO.") +
            "\\n\\nVocê pode desligar a qualquer momento.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if decision != QMessageBox.StandardButton.Yes:
            return
        self._session.begin(
            approved=True, contact=contact, listen_to_loud_sounds=microphone,
            seconds=1800
        )
        self._detector = SoundLevelDetector()
        self._pending.cancel()
        self._telegram_notifier = notifier
        self._alert_budget = AlertBudget()
        self._notification_epoch += 1
        self._cancel_send = threading.Event()
        self.recipient.setEnabled(False)
        self.sound_checkbox.setEnabled(False)
        self.telegram_checkbox.setEnabled(False)
        self.telegram_bot_token.setEnabled(False)
        self.telegram_chat_id.setEnabled(False)
        self.activate.setEnabled(False)
        self.sos.setEnabled(True)
        self.sos.setText(
            "SOS — Enviar alerta gratuito por Telegram" if notifier
            else "SOS — Preparar mensagem no WhatsApp"
        )
        self.warning.clear()
        self.setWindowTitle("Yuna • Segurança ATIVA (temporária)")
        self.tick.start()
        if microphone and not self._start_microphone():
            self.stop_safety()
            self.warning.setText(
                "Não foi possível iniciar o microfone. Nada está sendo ouvido. "
                "Confira as permissões do Windows ou use apenas o SOS."
            )
            return
        self._update_indicator()
        self.state_changed.emit(
            "microfone ativo" if self._audio_mode else "SOS apenas"
        )

    def _start_microphone(self):
        try:
            from PySide6.QtMultimedia import (
                QAudioFormat, QAudioSource, QMediaDevices
            )
            device = QMediaDevices.defaultAudioInput()
            if device.isNull():
                return False
            requested = QAudioFormat()
            requested.setSampleRate(16000)
            requested.setChannelCount(1)
            requested.setSampleFormat(QAudioFormat.SampleFormat.Int16)
            if not device.isFormatSupported(requested):
                return False
            audio = QAudioSource(device, requested, self)
            audio.setBufferSize(16000 * 2 // 5)
            io = audio.start()
            if io is None:
                audio.deleteLater()
                return False
            self._audio = audio
            self._device = io
            io.readyRead.connect(self._received_audio)
            self._audio_mode = True
            return True
        except (RuntimeError, ImportError, AttributeError):
            return False

    def _received_audio(self):
        if self._device is None or not self.active or not self._audio_mode:
            return
        try:
            raw = bytes(self._device.readAll())
        except RuntimeError:
            self.stop_safety()
            return
        # Não salvar buffers, não calcular transcrições.
        rms = rms_pcm16le(raw)
        if self._detector.observe(rms):
            if self._pending.schedule():
                self.warning.setText(
                    "Som alto persistente detectado! Pode ser falso alarme. "
                    "Você tem 15 segundos para cancelar o aviso local."
                )
                self.cancel_warning.setVisible(True)

    def cancel_sound_alert(self):
        self._pending.cancel()
        self.warning.setText("Alerta de som cancelado pela pessoa no notebook.")
        self.cancel_warning.setVisible(False)

    def _tick(self):
        try:
            self._session.check()
        except PermissionError:
            self.stop_safety()
            self.warning.setText("A sessão expirou. Ative novamente se desejar.")
            return
        if self._pending.consume_if_ready():
            self.cancel_warning.setVisible(False)
            if self._telegram_notifier is not None:
                self.warning.setText(
                    "Som alto: solicitando alerta gratuito ao Telegram. "
                    "Entrega no celular ainda não confirmada."
                )
                self._send_telegram_event("som_alto")
            else:
                self.warning.setText(
                    "Som alto detectado. Verifique se está tudo bem. "
                    "Nenhum aviso remoto foi enviado."
                )
                self._offer_whatsapp_draft("som_alto")
        self._update_indicator()

    def _update_indicator(self):
        left = int(self._session.remaining())
        label = "MICROFONE ATIVO — análise somente de volume" if self._audio_mode else (
            "SOS ATIVO — microfone desligado"
        )
        self.state.setText(
            "SEGURANÇA ATIVA · " + label +
            " · restante: " + str(left // 60) + " min"
        )

    def _offer_whatsapp_draft(self, kind):
        try:
            contact = self._session.check()
        except PermissionError:
            return
        question = QMessageBox.question(
            self, "Revisar alerta para contato de confiança",
            "Deseja abrir o WhatsApp com uma mensagem de " +
            ("SOS" if kind == "sos" else "som alto") +
            " pronta para revisar e ENVIAR manualmente?\n"
            "A Yuna não garante o envio nem acompanha a entrega.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if question == QMessageBox.StandardButton.Yes:
            address = whatsapp_draft_url(contact, kind)
            if not QDesktopServices.openUrl(QUrl(address)):
                self.warning.setText("Não consegui abrir o WhatsApp nesta máquina.")

    def _send_telegram_event(self, kind):
        """Envio numa thread com timeout, nunca bloqueando o Qt.

        Uma solicitação JÁ ENVIADA não pode ser recolhida. Parar impede
        disparos novos e ignora resultados de sessões anteriores.
        """
        try:
            self._session.check()
        except PermissionError:
            return False
        notifier = self._telegram_notifier
        if notifier is None or self._cancel_send.is_set():
            return False
        if not self._alert_budget.reserve(kind):
            self.warning.setText(
                "Limite/cooldown de alertas atingido. Nenhuma mensagem enviada."
            )
            return False
        epoch = self._notification_epoch
        cancel = self._cancel_send

        def work():
            if cancel.is_set():
                return
            try:
                success = notifier.send_event(kind)
            except (TelegramSendError, OSError, ValueError):
                success = False
            if not cancel.is_set():
                self._telegram_signals.completed.emit(epoch, success)

        threading.Thread(
            target=work, daemon=True, name="YunaTelegramSafetyAlert"
        ).start()
        return True

    def _on_telegram_result(self, epoch, success):
        if epoch != self._notification_epoch or not self.active:
            return
        if success:
            self.warning.setText(
                "Telegram aceitou a solicitação. A chegada/leitura no "
                "celular NÃO foi confirmada. Se houver risco, ligue."
            )
        else:
            self.warning.setText(
                "Falha ao solicitar o alerta pelo Telegram. Nenhum "
                "envio via WhatsApp pago foi tentado. Entre em contato "
                "por outros meios."
            )

    def send_sos_draft(self):
        if not self.active:
            return
        if self._telegram_notifier is None:
            self._offer_whatsapp_draft("sos")
            return
        decision = QMessageBox.question(
            self, "Enviar SOS via Telegram gratuito?",
            "Deseja enviar AGORA um pedido de ajuda ao contato configurado "
            "no Telegram? O serviço externo receberá apenas a mensagem "
            "predefinida de SOS, sem áudio ou imagens.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if decision == QMessageBox.StandardButton.Yes:
            self.warning.setText(
                "Solicitando SOS ao Telegram; entrega ainda não confirmada."
            )
            self._send_telegram_event("sos")

    def stop_safety(self):
        self._pending.cancel()
        self._cancel_send.set()
        self._notification_epoch += 1
        self._telegram_notifier = None
        self._session.stop()
        self.tick.stop()
        self._audio_mode = False
        if self._audio is not None:
            try:
                self._audio.stop()
                self._audio.deleteLater()
            except RuntimeError:
                pass
        self._audio = None
        self._device = None
        self.activate.setEnabled(True)
        self.sos.setEnabled(False)
        self.sos.setText("SOS — Preparar mensagem de ajuda")
        self.telegram_checkbox.setEnabled(True)
        self.telegram_bot_token.clear()  # nunca persistir segredo na UI
        self.telegram_bot_token.setEnabled(self.telegram_checkbox.isChecked())
        self.telegram_chat_id.setEnabled(self.telegram_checkbox.isChecked())
        self.recipient.setEnabled(True)
        self.sound_checkbox.setEnabled(True)
        self.cancel_warning.setVisible(False)
        self.state.setText("DESLIGADO — nenhuma captura ativa")
        self.setWindowTitle("Yuna • Segurança doméstica DESLIGADA")
        self.state_changed.emit("desligado")

    def closeEvent(self, event):
        self.stop_safety()
        super().closeEvent(event)
