param([Parameter(Mandatory=$true)][string]$Python,
      [ValidateSet('Ativar','Desativar')][string]$Inicializacao)
$ErrorActionPreference = 'Stop'
$rootPath = Split-Path -Parent $PSScriptRoot
$installedExe = Join-Path (Split-Path -Parent $rootPath) 'Yuna.exe'
if (Test-Path -LiteralPath (Join-Path $rootPath 'installed-app.json')) {
    if (-not (Test-Path -LiteralPath $installedExe)) { throw 'Yuna.exe ausente. Reinstale o app.' }
    $target = $installedExe
    $prefix = ''
} else {
    $target = Join-Path (Split-Path -Parent $Python) 'pythonw.exe'
    if (-not (Test-Path -LiteralPath $target)) { throw 'Python grafico indisponivel.' }
    $prefix = '"' + (Join-Path $rootPath 'yuna_launcher.py') + '" '
}
$shell = New-Object -ComObject WScript.Shell
function WriteShortcut([string]$folder, [string]$mode) {
    $shortcut = $shell.CreateShortcut((Join-Path $folder 'Yuna.app.lnk'))
    $shortcut.TargetPath = $target
    $shortcut.Arguments = $prefix + $mode
    $shortcut.WorkingDirectory = $rootPath
    $shortcut.Description = 'Yuna - conversa, personagem e Central'
    $shortcut.Save()
}
WriteShortcut ([Environment]::GetFolderPath('DesktopDirectory')) '--compact'
WriteShortcut ([Environment]::GetFolderPath('Programs')) '--compact'
$startup = [Environment]::GetFolderPath('Startup')
if ($Inicializacao -eq 'Ativar') { WriteShortcut $startup '--background' }
if ($Inicializacao -eq 'Desativar') {
    $path = Join-Path $startup 'Yuna.app.lnk'
    if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path }
}
