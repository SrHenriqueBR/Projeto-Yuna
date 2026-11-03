param([switch]$SemPerguntas, [switch]$IniciarComWindows, [switch]$RemoverInicializacao)
$ErrorActionPreference = 'Stop'
$rootPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$startupPath = Join-Path ([Environment]::GetFolderPath('Startup')) 'Yuna.app.lnk'
try {
    if ($RemoverInicializacao) {
        if (Test-Path -LiteralPath $startupPath) { Remove-Item -LiteralPath $startupPath }
        Write-Host 'Inicializacao automatica da Yuna removida.'
        exit 0
    }
    $pyw = (Get-Command pyw -ErrorAction Stop).Source
    $launcher = Join-Path $rootPath 'yuna_launcher.py'
    if (-not (Test-Path -LiteralPath $launcher -PathType Leaf)) { throw 'Launcher ausente.' }
    $shell = New-Object -ComObject WScript.Shell
    $folders = @([Environment]::GetFolderPath('DesktopDirectory'), [Environment]::GetFolderPath('Programs'))
    foreach ($folder in $folders) {
        $shortcut = $shell.CreateShortcut((Join-Path $folder 'Yuna.app.lnk'))
        $shortcut.TargetPath = $pyw
        $shortcut.Arguments = '-3 "' + $launcher + '" --compact'
        $shortcut.WorkingDirectory = $rootPath
        $shortcut.Description = 'Yuna.app - assistente local e chat compacto'
        $shortcut.Save()
    }
    Write-Host 'Yuna.app criada na Area de Trabalho e no menu Iniciar.'
    if (-not $SemPerguntas -and -not $IniciarComWindows) {
        $choice = Read-Host 'Iniciar Yuna.app em segundo plano ao entrar no Windows? [s/N]'
        $IniciarComWindows = $choice -match '^(s|sim)$'
    }
    if ($IniciarComWindows) {
        $shortcut = $shell.CreateShortcut($startupPath)
        $shortcut.TargetPath = $pyw
        $shortcut.Arguments = '-3 "' + $launcher + '" --background'
        $shortcut.WorkingDirectory = $rootPath
        $shortcut.Description = 'Yuna.app - iniciar na bandeja desta conta'
        $shortcut.Save()
        Write-Host 'Inicializacao automatica ativada para esta conta. Microfone e camera continuam opt-in por sessao.'
    }
    Write-Host 'Para remover a inicializacao automatica: configurar_yuna_app.ps1 -RemoverInicializacao'
    Write-Host 'Mantenha a pasta do projeto neste local. Fechar a janela recolhe para a bandeja; use Sair da Yuna para encerrar.'
} catch {
    Write-Error ('Nao consegui configurar os atalhos: ' + $_.Exception.Message)
    exit 1
}
