"""Observação local e leve de RAM/espaço em disco, exclusiva do Windows.

Não lê nomes de processos, dados pessoais, arquivos, temperatura, tela
ou webcam. Não conecta a rede nem chama IA. Alertas exigem duas leituras
consecutivas e limite de frequência para não incomodar.
"""
import ctypes
from dataclasses import dataclass
from pathlib import Path
import shutil
import sys
import time


class _MemoryStatus(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


@dataclass(frozen=True)
class HealthReading:
    ram_percent: int | None
    disk_free_gb: float | None
    disk_free_percent: float | None


def read_health():
    """Metadados agregados de memória e disco locais. None se indisponíveis."""
    if sys.platform != "win32":
        return None
    ram = None
    try:
        state = _MemoryStatus()
        state.dwLength = ctypes.sizeof(_MemoryStatus)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(state)):
            if 0 <= state.dwMemoryLoad <= 100:
                ram = int(state.dwMemoryLoad)
    except (OSError, AttributeError, ValueError):
        pass
    free_gb = free_pct = None
    try:
        # Apenas espaço da unidade do perfil Windows; nunca lista arquivos.
        anchor = Path.home().anchor
        disk = shutil.disk_usage(anchor)
        if disk.total > 0:
            free_gb = round(disk.free / (1024 ** 3), 1)
            free_pct = round(disk.free / disk.total * 100, 1)
    except (OSError, ValueError, ZeroDivisionError):
        pass
    if ram is None and free_gb is None:
        return None
    return HealthReading(ram, free_gb, free_pct)


def summary(reading):
    if reading is None:
        return "Dados de saúde do Windows indisponíveis no momento."
    ram = (f"{reading.ram_percent}% em uso"
           if reading.ram_percent is not None else "indisponível")
    disk = (f"{reading.disk_free_gb:.1f} GB livres ({reading.disk_free_percent:.1f}%)"
            if reading.disk_free_gb is not None and reading.disk_free_percent is not None
            else "indisponível")
    return ("Verificação local, sem leitura de arquivos ou processos.\n"
            "Memória RAM: " + ram + "\nEspaço livre na unidade do Windows: " + disk
            + "\n\nA Yuna apenas orienta; não fecha programas ou apaga arquivos.")


class HealthGuidance:
    def __init__(self, *, cooldown_seconds=3600):
        self.cooldown = max(0, float(cooldown_seconds))
        self._counts = {"ram": 0, "disk": 0}
        self._last = {}

    def reset(self):
        self._counts = {"ram": 0, "disk": 0}

    def observe(self, reading, *, now=None):
        if reading is None:
            self.reset()
            return ()
        moment = time.monotonic() if now is None else float(now)
        ram_high = reading.ram_percent is not None and reading.ram_percent >= 90
        disk_low = (reading.disk_free_gb is not None
                    and reading.disk_free_percent is not None
                    and (reading.disk_free_gb < 3 or reading.disk_free_percent < 4))
        lines = []
        for key, high, message in (
            ("ram", ram_high,
             "A memória RAM está muito ocupada ({}%). Se notar lentidão, feche programas que não usa; não vou encerrá-los sozinha.".format(reading.ram_percent)),
            ("disk", disk_low,
             "A unidade do Windows está com pouco espaço livre ({} GB). Revise seus arquivos e backups antes de apagar qualquer coisa.".format(reading.disk_free_gb)),
        ):
            self._counts[key] = self._counts[key] + 1 if high else 0
            last = self._last.get(key, float("-inf"))
            if self._counts[key] >= 2 and moment - last >= self.cooldown:
                self._last[key] = moment
                lines.append(message)
        return tuple(lines)
