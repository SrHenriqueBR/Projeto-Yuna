"""Eventos nativos → consulta em worker → aviso curto no thread da interface."""
import ctypes
import sys
from threading import Thread

from PySide6.QtCore import QAbstractNativeEventFilter, QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication

from plug_sense import PlugSnapshot, PlugTracker, read_plugs


class PlugEvents(QAbstractNativeEventFilter):
    def __init__(self, monitor):
        super().__init__()
        self.monitor = monitor

    def nativeEventFilter(self, event_type, message):
        if sys.platform == "win32" and bytes(event_type) in (
                b"windows_generic_MSG", b"windows_dispatcher_MSG"):
            from ctypes.wintypes import MSG
            if int(message):
                msg = ctypes.cast(int(message), ctypes.POINTER(MSG)).contents
                self.monitor.native_event(msg.message, msg.wParam)
        # Só observa: nunca consome mensagens do Windows ou veta a remoção.
        return False, 0


class PlugMonitor(QObject):
    notice = Signal(str)
    power_changed = Signal()
    completed = Signal(int, object)

    def __init__(self, parent=None, reader=read_plugs):
        super().__init__(parent)
        self.reader = reader
        self.active = False
        self.generation = 0
        self.inflight = None
        self.pending = False
        self.suspended = False
        self.snapshot = None
        self.tracker = PlugTracker()
        self.events = PlugEvents(self)
        self.debounce = QTimer(self)
        self.debounce.setSingleShot(True)
        self.debounce.setInterval(1500)
        self.debounce.timeout.connect(self._refresh)
        self.fallback = QTimer(self)
        self.fallback.setInterval(60000)
        self.fallback.timeout.connect(self.request_refresh)
        self.completed.connect(self._received)

    def start(self):
        if self.active or sys.platform != "win32":
            return
        self.active = True
        self.suspended = False
        self.generation += 1
        self.tracker = PlugTracker()
        self.snapshot = None
        QApplication.instance().installNativeEventFilter(self.events)
        self.fallback.start()
        self.request_refresh()

    def stop(self):
        if self.active:
            QApplication.instance().removeNativeEventFilter(self.events)
        self.active = False
        self.generation += 1
        self.debounce.stop()
        self.fallback.stop()
        self.pending = False
        self.snapshot = None
        self.tracker = PlugTracker()

    def request_refresh(self):
        if not self.active or self.suspended:
            return
        if self.inflight is not None:
            self.pending = True
        elif not self.debounce.isActive():
            # Uma rajada de devnodes (dock/composto) gera uma consulta, sem adiar para sempre.
            self.debounce.start()

    def native_event(self, message, event):
        if not self.active:
            return
        if message == 0x0219 and event in (0x0007, 0x8000, 0x8004):  # WM_DEVICECHANGE
            self.request_refresh()
        elif message == 0x0218:  # WM_POWERBROADCAST
            if event in (4, 7, 0x12):  # suspend / resume suspend / resume automatic
                self.suspended = event == 4
                self.generation += 1
                self.snapshot = None
                self.tracker = PlugTracker()
                self.debounce.stop()
                self.pending = False
                self.request_refresh()
            elif event in (0x0A, 0x8013):  # power status / power setting change
                self.request_refresh()

    def _refresh(self):
        if not self.active or self.suspended:
            return
        if self.inflight is not None:
            self.pending = True
            return
        token = self.generation
        self.inflight = token
        self.pending = False

        def collect():
            try:
                snapshot = self.reader()
            except Exception:
                snapshot = PlugSnapshot(None, None)
            try:
                self.completed.emit(token, snapshot)
            except RuntimeError:
                pass  # Janela já destruída; worker daemon não retém a aplicação.

        Thread(target=collect, name="Yuna-plugs", daemon=True).start()

    def _received(self, token, snapshot):
        if self.inflight == token:
            self.inflight = None
        if self.active and not self.suspended and token == self.generation:
            self.snapshot = snapshot
            message, changed = self.tracker.observe(snapshot)
            if changed:
                self.power_changed.emit()
            if message:
                self.notice.emit(message)
        if self.active and self.pending:
            self.pending = False
            self.request_refresh()
