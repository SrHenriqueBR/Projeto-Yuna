"""Detecção local e não invasiva de capacidade no Windows.

Consulta RAM e memória dedicada da GPU via PowerShell/CIM, com tempo limite.
Não envia dados pela rede e falha de modo conservador.
"""
import json
import os
import subprocess
import sys

from hardware_profiles import recommend_profile


_PS_SCRIPT = (
    "$ErrorActionPreference='Stop'; "
    "$ram=[math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory/1GB,2); "
    "$gpu=@(Get-CimInstance Win32_VideoController | "
    "Select-Object -ExpandProperty AdapterRAM); "
    "$vram=0; foreach($v in $gpu) { "
    "if($null -ne $v -and [double]$v -gt $vram) {$vram=[double]$v} }; "
    "@{ram_gb=$ram;vram_gb=[math]::Round($vram/1GB,2)} | ConvertTo-Json -Compress"
)


def detect_hardware(timeout=5):
    """Retorna RAM/VRAM estimadas ou None; VRAM do WMI pode ser limitada a 4 GB."""
    if sys.platform != "win32":
        return None
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", _PS_SCRIPT],
            capture_output=True, text=True, timeout=timeout, check=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        data = json.loads(result.stdout.strip())
        ram = float(data["ram_gb"])
        vram = float(data["vram_gb"])
        if not (0 < ram < 2048 and 0 <= vram < 256):
            return None
        return {"ram_gb": ram, "vram_gb": vram}
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError):
        return None


def detected_profile(environ=None):
    """Respeita override do usuário e usa detecção quando disponível."""
    from hardware_profiles import select_profile
    env = os.environ if environ is None else environ
    hardware = detect_hardware() or {"ram_gb": 8, "vram_gb": 0}
    return select_profile(hardware["ram_gb"], hardware["vram_gb"], env)
