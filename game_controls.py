"""Teclas curtas apenas para o jogo autorizado e em primeiro plano no Windows."""
import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import os
from pathlib import PureWindowsPath
import time

from companion_commands import banking_action
from game_sessions import normalize_executable


KEYS = {"move_forward": 0x57, "move_backward": 0x53,
        "move_left": 0x41, "move_right": 0x44, "look_left": 0x25,
        "look_right": 0x27, "jump": 0x20, "interact": 0x45,
        "crouch": 0x43, "pause": 0x1B}
DENIED = {"chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe",
          "explorer.exe", "cmd.exe", "powershell.exe", "pwsh.exe", "python.exe",
          "pythonw.exe", "notepad.exe", "code.exe", "windowsterminal.exe"}


def allowed_game(path):
    value = normalize_executable(path)
    parts = PureWindowsPath(value)
    if (parts.name in DENIED or "windows" in parts.parts or
            banking_action("abrir " + parts.stem)):
        raise PermissionError("Selecione o executável de um jogo; navegadores, bancos e ferramentas do sistema não são aceitos.")
    return value


@dataclass(frozen=True)
class Foreground:
    window: int
    pid: int
    executable: str


class WindowsInput:
    def __init__(self):
        if os.name != "nt":
            raise RuntimeError("Controle de jogos disponível somente no Windows.")
        self.user = ctypes.WinDLL("user32", use_last_error=True)
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.user.GetForegroundWindow.restype = wintypes.HWND
        self.user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        self.kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        self.kernel.OpenProcess.restype = wintypes.HANDLE
        self.kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
        self.kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        self.user.GetAsyncKeyState.argtypes = [ctypes.c_int]
        self.user.GetAsyncKeyState.restype = ctypes.c_short
        self.user.MapVirtualKeyW.argtypes = [wintypes.UINT, wintypes.UINT]
        self.user.MapVirtualKeyW.restype = wintypes.UINT

    def foreground(self):
        window = self.user.GetForegroundWindow()
        if not window:
            raise PermissionError("Nenhuma janela em foco.")
        pid = wintypes.DWORD()
        self.user.GetWindowThreadProcessId(window, ctypes.byref(pid))
        process = self.kernel.OpenProcess(0x1000, False, pid.value)
        if not process:
            raise PermissionError("Não consegui conferir o processo do jogo.")
        try:
            size = wintypes.DWORD(32768)
            path = ctypes.create_unicode_buffer(size.value)
            if not self.kernel.QueryFullProcessImageNameW(process, 0, path, ctypes.byref(size)):
                raise PermissionError("Não consegui conferir o executável do jogo.")
            return Foreground(int(window), pid.value, normalize_executable(path.value))
        finally:
            self.kernel.CloseHandle(process)

    def key_is_down(self, vk):
        return bool(self.user.GetAsyncKeyState(vk) & 0x8000)

    def key(self, vk, *, release):
        ulong_ptr = ctypes.c_size_t
        class Mouse(ctypes.Structure):
            _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG),
                        ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                        ("time", wintypes.DWORD), ("dwExtraInfo", ulong_ptr)]
        class Keyboard(ctypes.Structure):
            _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                        ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                        ("dwExtraInfo", ulong_ptr)]
        class Hardware(ctypes.Structure):
            _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD), ("wParamH", wintypes.WORD)]
        class Values(ctypes.Union):
            _fields_ = [("mi", Mouse), ("ki", Keyboard), ("hi", Hardware)]
        class Input(ctypes.Structure):
            _fields_ = [("type", wintypes.DWORD), ("value", Values)]
        flags = 0x0008 | (0x0002 if release else 0) | (0x0001 if vk in (0x25, 0x27) else 0)
        event = Input(type=1, value=Values(ki=Keyboard(
            0, self.user.MapVirtualKeyW(vk, 0), flags, 0, 0)))
        self.user.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(Input), ctypes.c_int]
        self.user.SendInput.restype = wintypes.UINT
        if self.user.SendInput(1, ctypes.byref(event), ctypes.sizeof(Input)) != 1:
            raise RuntimeError("O Windows ou o jogo recusou a tecla. Não há tentativa de contornar essa restrição.")


def execute_action(session, action, cancelled, backend=None, clock=time.monotonic, sleep=time.sleep):
    """Uma ação humana por chamada. Libera a tecla mesmo em erro/parada/troca de foco."""
    if action not in KEYS:
        raise ValueError("Ação de jogo desconhecida.")
    backend = backend or WindowsInput()
    if cancelled():
        raise InterruptedError("Controle cancelado.")
    original = backend.foreground()
    allowed_game(original.executable)
    proposal = session.propose(action, foreground_executable=original.executable, seconds=.15)
    key = KEYS[action]
    # Evita atalhos acidentais (por exemplo Win+E), inclusive tecla já segurada.
    if any(backend.key_is_down(vk) for vk in (0x10, 0x11, 0x12, 0x5B, 0x5C, key)):
        raise PermissionError("Solte as teclas do teclado antes do comando da Yuna.")
    if cancelled() or not session.active or backend.foreground() != original:
        session.stop()
        raise InterruptedError("O foco mudou; nenhuma tecla foi enviada.")
    pressed = False
    try:
        backend.key(key, release=False)
        pressed = True
        deadline = clock() + proposal.seconds
        while clock() < deadline:
            if (cancelled() or not session.active or backend.foreground() != original or
                    any(backend.key_is_down(vk) for vk in (0x10, 0x11, 0x12, 0x5B, 0x5C))):
                session.stop()
                raise InterruptedError("Controle interrompido e tecla liberada.")
            sleep(.01)
    finally:
        if pressed:
            backend.key(key, release=True)
    return "Enviei uma tecla curta ao jogo autorizado. O efeito depende dos controles do jogo."
