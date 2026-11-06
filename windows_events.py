"""Eventos agregados do Windows, somente sob comando da pessoa.

Nenhuma elevação, leitura de mensagens dos logs, nome de usuário,
arquivo, caminho, SID ou evento de segurança. O PowerShell executa um
script estático, sem interpolação de entrada. Nenhuma correção automática.
"""
import json
import os
from pathlib import Path
import subprocess
import sys

ALLOWED_LOGS = {"System", "Application"}
# Script fechado, independente de argumentos fornecidos por outras partes.
_SCRIPT = (
    "$ErrorActionPreference='Stop'; "
    "[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false); "
    "$log=$env:YUNA_WINLOG; "
    "if($log -notin @('System','Application')) { throw 'Log inválido' }; "
    "try { $items = @(Get-WinEvent -FilterHashtable "
    "@{LogName=$log; Level=@(1,2,3); StartTime=(Get-Date).AddDays(-1)} "
    "-MaxEvents 15 -ErrorAction Stop | "
    "Select-Object @{Name='Quando';Expression={$_.TimeCreated.ToString('s')}},"
    "@{Name='Origem';Expression={$_.ProviderName}},"
    "@{Name='Codigo';Expression={$_.Id}},"
    "@{Name='Nivel';Expression={$_.LevelDisplayName}}) } catch { "
    "if ($_.FullyQualifiedErrorId -like 'NoMatchingEventsFound*') { $items = @() } "
    "else { throw } }; "
    "ConvertTo-Json -InputObject $items -Compress -Depth 3"
)


def read_recent_events(log="System", *, runner=None):
    if sys.platform != "win32":
        return "A consulta de eventos está disponível somente no Windows."
    if log not in ALLOWED_LOGS:
        raise ValueError("Escolha System ou Application.")
    env = dict(os.environ)
    env["YUNA_WINLOG"] = log
    # Nunca executar cmd/PowerShell composto com dados livres do usuário.
    run = runner or subprocess.run
    powershell = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    try:
        proc = run([str(powershell), "-NoProfile", "-NonInteractive",
                    "-ExecutionPolicy", "Bypass", "-Command", _SCRIPT],
                   shell=False, capture_output=True, text=True,
                   encoding="utf-8-sig", errors="replace",
                   timeout=22, env=env,
                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("Não consegui consultar os eventos do Windows.") from exc
    if proc.returncode:
        return ("Não consegui ler o log " + log + ". A consulta falhou ou "
                "sua conta não tem permissão para consultá-lo.")
    if len(proc.stdout) > 40000:
        raise ValueError("Resposta de eventos acima do limite.")
    try:
        entries = json.loads(proc.stdout)
    except (ValueError, TypeError) as exc:
        raise RuntimeError("O Windows não retornou eventos no formato esperado.") from exc
    if isinstance(entries, dict):
        entries = [entries]
    if not isinstance(entries, list):
        raise ValueError("Eventos em formato inesperado.")
    lines = [f"Eventos de aviso/erro do log {log} — últimas 24 horas:",
             "Apenas data, nível, código e provedor. Nenhuma mensagem privada foi coletada."]
    for event in entries[:15]:
        if not isinstance(event, dict):
            continue
        # Qualquer valor retornado é dado não confiável, limitado em tamanho.
        when = str(event.get("Quando", ""))[:22]
        origin = str(event.get("Origem", ""))[:75].replace("\n", " ")
        code = str(event.get("Codigo", ""))[:12]
        level = str(event.get("Nivel", ""))[:35]
        lines.append(f"• {when} · {level} · Evento {code} · {origin}")
    if len(lines) == 2:
        lines.append("Nenhum evento retornado na seleção.")
    lines.append("A Yuna não alterou nenhum serviço, driver ou configuração.")
    return "\n".join(lines)
