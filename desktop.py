"""Ferramentas locais do Windows: catálogo de apps e consultas de diagnóstico."""
import json
import os
from pathlib import Path
import subprocess
from computer import normalize

SCRIPTS = {
    'apps': 'Get-StartApps | Select-Object Name,AppID | ConvertTo-Json -Compress',
    'processes': '''Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 20 ProcessName,Id,@{Name='RAM_MB';Expression={[math]::Round($_.WorkingSet64/1MB,1)}} | ConvertTo-Json -Compress''',
    'system': '''$osInfo=Get-CimInstance Win32_OperatingSystem; $cpuInfo=Get-CimInstance Win32_Processor | Select-Object -First 1; $gpuInfo=@(Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name); $diskInfo=@(Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3' | Select-Object DeviceID,@{Name='Livre_GB';Expression={[math]::Round($_.FreeSpace/1GB,1)}},@{Name='Total_GB';Expression={[math]::Round($_.Size/1GB,1)}}); [pscustomobject]@{Windows=$osInfo.Caption;CPU=$cpuInfo.Name;RAM_total_GB=[math]::Round($osInfo.TotalVisibleMemorySize/1MB,1);RAM_livre_GB=[math]::Round($osInfo.FreePhysicalMemory/1MB,1);GPU=$gpuInfo;Discos=$diskInfo} | ConvertTo-Json -Depth 4 -Compress''',
}


def query_windows(kind):
    if kind not in SCRIPTS:
        raise ValueError('Consulta desconhecida.')
    if os.name != 'nt':
        raise RuntimeError('Esta consulta exige Windows.')
    powershell = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
    script = "$ErrorActionPreference='Stop'; [Console]::OutputEncoding=[System.Text.UTF8Encoding]::new(); " + SCRIPTS[kind]
    try:
        result = subprocess.run([str(powershell), '-NoProfile', '-NonInteractive', '-Command', script],
                                capture_output=True, encoding='utf-8', errors='replace', timeout=25,
                                shell=False, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if result.returncode:
            raise RuntimeError('A consulta ao Windows falhou: ' + result.stderr.strip()[:400])
        return json.loads(result.stdout.lstrip('\ufeff').strip() or 'null')
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError('O Windows demorou demais para responder. Tente novamente.') from exc
    except (OSError, ValueError) as exc:
        raise RuntimeError(f'Não consegui consultar o Windows: {exc}') from exc


class Desktop:
    def __init__(self):
        self.catalog = None
        self.choices = []

    def refresh(self):
        self.catalog = None
        self.choices = []
        rows = query_windows('apps') or []
        if isinstance(rows, dict):
            rows = [rows]
        if not isinstance(rows, list):
            raise RuntimeError('Catálogo de aplicativos inválido.')
        clean = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            name, appid = row.get('Name'), row.get('AppID')
            if not isinstance(name, str) or not isinstance(appid, str):
                continue
            if not name.strip() or not appid.strip() or any(c in appid for c in '\r\n\x00'):
                continue
            clean[appid] = {'name': name.strip(), 'id': appid}
        self.catalog = sorted(clean.values(), key=lambda app: normalize(app['name']))

    def matches(self, name):
        if self.catalog is None:
            self.refresh()
        terms = normalize(name).split()
        exact = [app for app in self.catalog if normalize(app['name']) == normalize(name)]
        return exact or [app for app in self.catalog if all(term in normalize(app['name']) for term in terms)]

    def list_apps(self, query=''):
        self.choices = self.matches(query)
        if not self.choices:
            return 'Não encontrei esse programa no catálogo do menu Iniciar. Use /apps atualizar após instalar um programa.'
        self.choices = self.choices[:100]
        return '\n'.join([f'{i}. {app["name"]}' for i, app in enumerate(self.choices, 1)] +
                         ['Lista de até 100 aplicativos. Use /app NUMERO para abrir ou /apps NOME para filtrar.'])

    def open_app(self, name):
        if not isinstance(name, str) or not name.strip() or len(name) > 100:
            raise ValueError('Informe o nome do aplicativo.')
        matches = self.matches(name)
        if len(matches) != 1:
            return self.list_apps(name)
        return self.launch(matches[0])

    def launch(self, app):
        if not self.catalog or app not in self.catalog:
            raise ValueError('Aplicativo não pertence ao catálogo do Windows.')
        if os.name != 'nt':
            return 'A abertura de aplicativos exige Windows.'
        explorer = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'explorer.exe'
        try:
            subprocess.Popen([str(explorer), 'shell:AppsFolder\\' + app['id']], shell=False)
        except OSError as exc:
            return f'Não consegui solicitar a abertura de {app["name"]}: {exc}'
        return f'Solicitei ao Windows a abertura de {app["name"]}. Confira a janela do aplicativo.'

    def open_choice(self, number):
        if number < 1 or number > len(self.choices):
            return 'Número de aplicativo inválido. Use /apps para listar.'
        return self.launch(self.choices[number - 1])

    def system_info(self):
        return 'Informações consultadas agora no Windows:\n' + json.dumps(query_windows('system'), ensure_ascii=False, indent=2)

    def processes(self):
        return 'Até 20 processos com maior memória RAM (MB), sem encerrar nenhum:\n' + json.dumps(query_windows('processes'), ensure_ascii=False, indent=2)
