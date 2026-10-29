"""Prévia voluntária de câmera em janela Qt, sem gravação ou inferência facial.

O OpenCV é opcional e importado somente depois de consentimento. Frames ficam
na memória da UI, nunca vão a Ollama, nuvem, arquivos ou ao chat.
"""
import os
import sys
import threading
import time

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QImage, QPixmap, QShortcut, QKeySequence
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
)

from camera_watch import CameraPermission
from camera_motion import MotionChangeDetector


class CameraSignals(QObject):
    frame_ready = Signal(QImage)
    failed = Signal(str)
    finished = Signal()
    motion_detected = Signal()


class CameraViewer(QDialog):
    def __init__(self, permission: CameraPermission, parent=None):
        super().__init__(parent)
        self._permission = permission
        self._stop = threading.Event()
        self._worker = None
        self._motion_enabled = threading.Event()
        self._signals = CameraSignals(self)
        self._signals.frame_ready.connect(self.show_frame)
        self._signals.failed.connect(self.show_error)
        self._signals.finished.connect(self.worker_finished)
        self._signals.motion_detected.connect(self.motion_warning)

        self.setWindowTitle("Yuna • Câmera autorizada")
        self.resize(860, 550)
        self.setMinimumSize(480, 320)
        self.setStyleSheet(
            "QDialog{background:#151222;color:#eee8f5;}"
            "QPushButton{background:#513c76;color:white;padding:10px;"
            "border-radius:8px;} QLabel{color:#eee8f5;}"
        )
        layout = QVBoxLayout(self)
        self.preview = QLabel("Preparando prévia autorizada...")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumSize(400, 200)
        self.preview.setStyleSheet(
            "background:#090811;border:1px solid #51406e;"
            "border-radius:10px;"
        )
        layout.addWidget(self.preview, 1)
        self.status = QLabel("Esta sessão não grava, transmite nem analisa imagens.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.motion_checkbox = QCheckBox(
            "Detectar mudanças de imagem localmente (sem fotos, nem alertas remotos)"
        )
        self.motion_checkbox.setChecked(False)
        self.motion_checkbox.toggled.connect(self.toggle_motion)
        layout.addWidget(self.motion_checkbox)
        buttons = QHBoxLayout()
        self.stop_button = QPushButton("■ Encerrar câmera")
        self.stop_button.clicked.connect(self.close)
        buttons.addStretch()
        buttons.addWidget(self.stop_button)
        layout.addLayout(buttons)
        self.shortcut = QShortcut(QKeySequence("Ctrl+Shift+X"), self)
        self.shortcut.activated.connect(self.close)
        self._last_frame = None
        self._timer = QTimer(self)
        self._timer.setInterval(500)
        self._timer.timeout.connect(self._check_permission)

    def toggle_motion(self, enabled):
        """A análise não liga se a pessoa não marcar a opção."""
        if enabled:
            self._motion_enabled.set()
            self.status.setText(
                "Detecção de alterações ATIVA • sem gravação ou identificação"
            )
        else:
            self._motion_enabled.clear()
            self.status.setText("Detecção de movimento DESLIGADA")

    def motion_warning(self):
        if not self._stop.is_set() and self.isVisible():
            self.status.setText(
                "Mudança de imagem detectada! Pode ser movimento ou luz. "
                "Nenhuma mensagem remota foi enviada."
            )

    def start_preview(self):
        if self._worker is not None:
            return
        try:
            source = self._permission.check()
        except PermissionError:
            self.status.setText("Autorização de câmera inválida.")
            return
        self.status.setText(
            source.label + " • prévia local ativa • "
            "Ctrl+Shift+X ou Encerrar para parar"
        )
        self._timer.start()
        self._worker = threading.Thread(
            target=self._read_stream, args=(source,),
            name="YunaCameraPreview", daemon=True
        )
        self._worker.start()

    def _read_stream(self, source):
        cap = None
        try:
            import cv2
        except ImportError:
            self._signals.failed.emit(
                "Para abrir câmeras, instale OpenCV: py -3 -m pip install opencv-python"
            )
            self._signals.finished.emit()
            return
        try:
            if source.kind == "webcam":
                if sys.platform == "win32":
                    cap = cv2.VideoCapture(source.index, cv2.CAP_DSHOW)
                else:
                    cap = cv2.VideoCapture(source.index)
            else:
                cap = cv2.VideoCapture(
                    source.url, cv2.CAP_FFMPEG,
                    [cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 3000,
                     cv2.CAP_PROP_READ_TIMEOUT_MSEC, 3000]
                )
            if not cap.isOpened():
                raise RuntimeError("Não consegui abrir esta câmera.")
            # Não contar com CAP_PROP_BUFFERSIZE: alguns backends ignoram.
            next_at = time.monotonic()
            motion = MotionChangeDetector()
            motion_previously_enabled = False
            while not self._stop.is_set():
                try:
                    self._permission.check()
                except PermissionError:
                    break
                ok, frame = cap.read()
                if not ok or frame is None:
                    raise RuntimeError(
                        "O fluxo de vídeo terminou ou a câmera ficou indisponível."
                    )
                height, width = frame.shape[:2]
                if height < 1 or width < 1:
                    continue
                if self._motion_enabled.is_set():
                    if not motion_previously_enabled:
                        motion.reset()
                    tiny = cv2.resize(frame, (64, 36), interpolation=cv2.INTER_AREA)
                    gray = cv2.cvtColor(tiny, cv2.COLOR_BGR2GRAY)
                    if motion.observe(gray.tobytes()):
                        self._signals.motion_detected.emit()
                    motion_previously_enabled = True
                else:
                    if motion_previously_enabled:
                        motion.reset()
                    motion_previously_enabled = False
                if width > 960:
                    factor = 960.0 / width
                    frame = cv2.resize(frame, (960, max(1, round(height * factor))))
                    height, width = frame.shape[:2]
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image = QImage(
                    rgb.data, width, height, rgb.strides[0],
                    QImage.Format.Format_RGB888
                ).copy()
                self._signals.frame_ready.emit(image)
                next_at += 0.1  # máximo 10 FPS na UI para economizar recursos
                sleep = max(0, next_at - time.monotonic())
                if self._stop.wait(sleep):
                    break
                if sleep == 0:
                    next_at = time.monotonic()
        except Exception:
            if not self._stop.is_set():
                # Não mostrar exception: OpenCV pode incluir URL/senha RTSP.
                self._signals.failed.emit(
                    "Não foi possível visualizar a câmera. Confira conexão, "
                    "permissão, endereço RTSP e se outro aplicativo a está usando."
                )
        finally:
            if cap is not None:
                try:
                    cap.release()
                except Exception:
                    pass
            self._signals.finished.emit()

    def _check_permission(self):
        try:
            self._permission.check()
        except PermissionError:
            self.status.setText("Tempo de acesso encerrado.")
            self.close()

    def show_frame(self, image):
        if self._stop.is_set() or not self.isVisible():
            return
        self._last_frame = image
        self.preview.setPixmap(QPixmap.fromImage(image).scaled(
            self.preview.size(), Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        ))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._last_frame is not None and self.isVisible():
            self.show_frame(self._last_frame)

    def show_error(self, error):
        if self._stop.is_set():
            return
        self.status.setText(error)
        self.preview.setText("Câmera indisponível.")
        self.stop_preview()

    def worker_finished(self):
        self._timer.stop()
        if not self._stop.is_set():
            self.status.setText("A prévia terminou.")
        self._permission.stop()

    def stop_preview(self):
        self._motion_enabled.clear()
        self._stop.set()
        self._permission.stop()
        self._timer.stop()
        self._last_frame = None
        self.preview.clear()

    def closeEvent(self, event):
        self.stop_preview()
        super().closeEvent(event)
