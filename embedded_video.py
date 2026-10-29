"""Janela opcional de reunião de vídeo dentro da Yuna Desktop.

O serviço Jitsi é externo; a webcam NUNCA é habilitada por comando Yuna.
Permissões de áudio/vídeo são de sessão, requerem interação visível de
quem usa esta máquina e ficam sob controle do cliente de reunião.
"""
from PySide6.QtCore import Qt, QUrl
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout,
)
from PySide6.QtGui import QDesktopServices

from remote_camera_invite import validate_remote_camera_invite


def _is_jitsi_origin(origin):
    if isinstance(origin, QUrl):
        return (origin.scheme() == "https" and
                origin.host().casefold() == "meet.jit.si" and
                origin.port(-1) in (-1, 443))
    return False


class EmbeddedVideoDialog(QDialog):
    """Prévia visível de sala HTTPS com controle de permissões no Qt."""

    def __init__(self, invitation, parent=None):
        super().__init__(parent)
        self._invite = validate_remote_camera_invite(invitation)
        self._view = None
        self._webengine_loaded = False
        self.setWindowTitle("Yuna • Videochamada autorizada (Jitsi externo)")
        self.resize(1024, 710)
        self.setMinimumSize(640, 440)
        self.setStyleSheet(
            "QDialog{background:#161226;color:#eee8fb;}"
            "QPushButton{background:#59427b;color:white;padding:10px;"
            "border-radius:7px;} QLabel{color:#eee8fb;}"
        )
        layout = QVBoxLayout(self)
        self.notice = QLabel(
            "Videochamada por Jitsi Meet (serviço externo). "
            "Cada participante escolhe quando compartilhar câmera e microfone. "
            "A Yuna não grava esta chamada."
        )
        self.notice.setWordWrap(True)
        layout.addWidget(self.notice)
        try:
            from PySide6.QtWebEngineWidgets import QWebEngineView
            view = QWebEngineView(self)
            self._view = view
            page = view.page()
            if hasattr(page, "permissionRequested"):
                page.permissionRequested.connect(self._request_permission)
            else:
                page.featurePermissionRequested.connect(
                    self._request_legacy_permission
                )
            layout.addWidget(view, 1)
            self._webengine_loaded = True
        except (ImportError, RuntimeError):
            info = QLabel(
                "A janela de vídeo embutida exige Qt WebEngine. "
                "Você ainda pode abrir a reunião no navegador padrão, "
                "com as mesmas opções de consentimento."
            )
            info.setAlignment(Qt.AlignmentFlag.AlignCenter)
            info.setWordWrap(True)
            layout.addWidget(info, 1)
        buttons = QHBoxLayout()
        external = QPushButton("Abrir em navegador externo")
        external.clicked.connect(self._open_external)
        buttons.addWidget(external)
        buttons.addStretch()
        close = QPushButton("■ Sair da chamada nesta janela")
        close.clicked.connect(self.close)
        buttons.addWidget(close)
        layout.addLayout(buttons)

    def start(self):
        """Não liga câmera; apenas carrega site HTTPS da sala."""
        if self._view is not None:
            self._view.setUrl(QUrl(self._invite))
        return self._webengine_loaded

    def _request_permission(self, permission):
        """Qt >=6.8: nunca lembrar permissão, negar origens não esperadas."""
        try:
            origin = permission.origin()
            type_name = str(permission.permissionType().name)
        except (AttributeError, RuntimeError):
            permission.deny()
            return
        if (not _is_jitsi_origin(origin) or
                type_name not in ("MediaAudioCapture", "MediaVideoCapture",
                                  "MediaAudioVideoCapture")):
            permission.deny()
            return
        decision = QMessageBox.question(
            self, "Permissão de mídia da chamada",
            "O Jitsi Meet deseja usar a câmera e/ou o microfone deste "
            "computador. A pessoa que está usando o notebook autoriza "
            "esse acesso nesta chamada? Você pode recusar.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if decision == QMessageBox.StandardButton.Yes:
            permission.grant()
        else:
            permission.deny()

    def _request_legacy_permission(self, origin, feature):
        from PySide6.QtWebEngineCore import QWebEnginePage
        features = QWebEnginePage.Feature
        allowed = (features.MediaAudioCapture, features.MediaVideoCapture,
                   features.MediaAudioVideoCapture)
        granted = _is_jitsi_origin(origin) and feature in allowed
        if granted:
            granted = (QMessageBox.question(
                self, "Permissão de mídia",
                "A pessoa que usa este notebook autoriza o Jitsi Meet "
                "a acessar câmera e/ou microfone nesta chamada?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            ) == QMessageBox.StandardButton.Yes)
        policy = (QWebEnginePage.PermissionPolicy.PermissionGrantedByUser
                  if granted else
                  QWebEnginePage.PermissionPolicy.PermissionDeniedByUser)
        self._view.page().setFeaturePermission(origin, feature, policy)

    def _open_external(self):
        if not QDesktopServices.openUrl(QUrl(self._invite)):
            QMessageBox.warning(
                self, "Navegador indisponível",
                "Não foi possível abrir o navegador nesta máquina."
            )

    def closeEvent(self, event):
        if self._view is not None:
            self._view.setUrl(QUrl("about:blank"))
        super().closeEvent(event)
