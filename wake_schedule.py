"""Um despertar agendado no Windows; não liga hardware totalmente desligado."""
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from companion_commands import command


def wake_intent(text, now=None):
    value = command(text)
    if value in ("/despertar", "mostre o horario de despertar"):
        return "consultar", None
    if value in ("/despertar cancelar", "cancele o despertar", "cancelar despertar"):
        return "cancelar", None
    match = re.fullmatch(
        r"(?:/despertar|acorde o computador|desperte o computador|"
        r"ligue o computador|liga o computador|agende o despertar) "
        r"(?:(hoje|amanha|\d{4}-\d{2}-\d{2}) )?(?:as )?(\d{1,2}):(\d{2})", value)
    if not match:
        return None
    moment = now or datetime.now()
    day, hour, minute = match.groups()
    try:
        selected = moment.replace(hour=int(hour), minute=int(minute), second=0, microsecond=0)
        if day == "amanha":
            selected += timedelta(days=1)
        elif day and day != "hoje":
            selected = datetime.combine(datetime.strptime(day, "%Y-%m-%d").date(), selected.time())
        elif not day and selected <= moment:
            selected += timedelta(days=1)
    except ValueError:
        raise ValueError("Horário inválido. Exemplo: Yuna, acorde o computador amanhã às 07:00.") from None
    if not moment + timedelta(minutes=1) <= selected <= moment + timedelta(days=7):
        raise ValueError("Escolha um horário de 1 minuto a 7 dias no futuro, no relógio deste computador.")
    return "agendar", selected


def run_wake_task(action, when=None):
    if action not in ("agendar", "cancelar", "consultar"):
        raise ValueError("Ação de despertar inválida.")
    if os.name != "nt":
        raise RuntimeError("O agendamento de despertar exige Windows.")
    if action == "agendar":
        if not isinstance(when, datetime) or when.tzinfo is not None:
            raise ValueError("Use uma data no horário local do computador.")
        if not datetime.now() < when <= datetime.now() + timedelta(days=7):
            raise ValueError("Horário fora do limite de sete dias.")
    root = Path(__file__).resolve().parent
    executable = Path(sys.executable)
    if executable.name.casefold() == "python.exe":
        executable = executable.with_name("pythonw.exe")
    environment = dict(os.environ)
    environment.update(YUNA_WAKE_TIME=when.isoformat(timespec="seconds") if when else "",
                       YUNA_WAKE_PYTHON=str(executable), YUNA_WAKE_ROOT=str(root))
    powershell = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    result = subprocess.run([str(powershell), "-NoProfile", "-NonInteractive",
                             "-ExecutionPolicy", "Bypass", "-File", str(root / "wake_schedule.ps1"),
                             "-Acao", action], env=environment, shell=False,
                            capture_output=True, encoding="utf-8", errors="replace", timeout=20,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if result.returncode:
        raise RuntimeError("O Windows recusou a tarefa de despertar. Verifique o Agendador de Tarefas e as permissões desta conta.")
    data = json.loads(result.stdout.lstrip("\ufeff").strip())
    if action == "agendar":
        return (f"Agendei uma tentativa de despertar para {when:%d/%m/%Y às %H:%M}, no horário deste computador. "
                "Deixe o Windows suspenso/hibernando e conectado à energia. Timers de ativação e hardware precisam permitir o despertar. "
                "Não funciona com o computador totalmente desligado. Para cancelar: /despertar cancelar.")
    if action == "cancelar":
        return "Removi o agendamento de despertar da Yuna." if data.get("removed") else "Não havia despertar da Yuna agendado."
    if not data.get("exists"):
        return "Não há despertar da Yuna agendado. Exemplo: /despertar amanhã às 07:00."
    return ("Tarefa de despertar da Yuna: " + str(data.get("state", "")) +
            ". Próxima execução informada pelo Windows: " + str(data.get("next_run", "")) +
            ". O despertar exige suspensão/hibernação compatível; não liga um PC totalmente desligado.")
