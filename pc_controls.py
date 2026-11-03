"""Diagnóstico local e desligamento solicitado, sem comandos livres ou limpeza."""
import math
import os
from pathlib import Path
import subprocess
import time

from companion_commands import command


SETTINGS = {
    "inicializacao": "ms-settings:startupapps",
    "armazenamento": "ms-settings:storagesense",
    "energia": "ms-settings:powersleep",
    "modo jogo": "ms-settings:gaming-gamemode",
}


def settings_intent(text):
    value = command(text)
    for label in SETTINGS:
        if value in ("/ajustes " + label, "abrir ajustes de " + label,
                     "abra os ajustes de " + label):
            return label
    return None


def open_settings(label):
    if label not in SETTINGS:
        raise ValueError("Ajuste desconhecido.")
    if os.name != "nt":
        return "Os ajustes do computador exigem Windows."
    os.startfile(SETTINGS[label], "open")
    return ("Solicitei a abertura dos ajustes de " + label +
            ". Escolha a alteração na janela do Windows.")


def performance_report(info):
    if not isinstance(info, dict):
        raise ValueError("O Windows não retornou o diagnóstico esperado.")
    lines = ["Diagnóstico atual do computador:"]
    total, free = info.get("RAM_total_GB"), info.get("RAM_livre_GB")
    if all(type(n) in (int, float) and math.isfinite(n) and n >= 0 for n in (total, free)) and total > 0:
        lines.append(f"RAM livre: {free:g} de {total:g} GB.")
        if free / total < .2:
            lines.append("Pouca RAM livre. Feche os programas que não está usando e confira /processos.")
    disks = info.get("Discos") or []
    if isinstance(disks, dict):
        disks = [disks]
    for disk in disks:
        if not isinstance(disk, dict):
            continue
        size, available = disk.get("Total_GB"), disk.get("Livre_GB")
        if all(type(n) in (int, float) and math.isfinite(n) and n >= 0 for n in (size, available)) and size > 0:
            lines.append(f"Disco {disk.get('DeviceID', '?')}: {available:g} de {size:g} GB livres.")
            if available / size < .15:
                lines.append("Pouco espaço. Confira /ajustes armazenamento antes de remover arquivos.")
    lines.extend([
        "Para revisar programas que iniciam com o PC: /ajustes inicializacao.",
        "Energia: /ajustes energia. Jogos: /ajustes modo jogo.",
        "Este diagnóstico não apaga arquivos, encerra processos, altera drivers ou garante mais FPS.",
    ])
    return "\n".join(lines)


def shutdown_windows():
    if os.name != "nt":
        raise RuntimeError("Desligamento disponível somente no Windows.")
    target = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "shutdown.exe"
    # A espera é nossa. /t > 0 implica /f no Windows e pode perder trabalho aberto.
    result = subprocess.run([str(target), "/s", "/t", "0"], shell=False,
                            capture_output=True, timeout=10,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if result.returncode:
        raise RuntimeError("O Windows recusou o desligamento; confira permissões e aplicativos abertos.")


class ShutdownCountdown:
    """Só executa no tick após a contagem. Parar ou encerrar Yuna cancela a espera."""
    def __init__(self, execute=shutdown_windows, clock=time.monotonic):
        self.execute, self.clock = execute, clock
        self.deadline = None

    def start(self):
        if self.deadline is None:
            self.deadline = self.clock() + 30

    def cancel(self):
        pending = self.deadline is not None
        self.deadline = None
        return pending

    def remaining(self):
        return None if self.deadline is None else max(0, math.ceil(self.deadline - self.clock()))

    def tick(self):
        if self.remaining() == 0:
            self.deadline = None
            self.execute()
            return True
        return False
