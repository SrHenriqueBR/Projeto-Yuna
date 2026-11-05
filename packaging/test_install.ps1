$ErrorActionPreference = 'Stop'
$rootPath = Split-Path -Parent $PSScriptRoot
$testRoot = Join-Path $env:RUNNER_TEMP 'Yuna Install Test'
$target = Join-Path $testRoot 'Installed'
$legacy = Join-Path $testRoot 'Yuna antiga'
New-Item -ItemType Directory -Force -Path (Join-Path $legacy 'data') | Out-Null
[System.IO.File]::WriteAllText((Join-Path $legacy 'data\memoria-teste.txt'), 'preservar a memoria', [System.Text.Encoding]::UTF8)
$setup = Join-Path $rootPath 'dist\Yuna-Setup.exe'
function InstallYuna {
    $arguments = '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP- /TASKS="" /DIR="' + $target + '" /YUNAMIGRATE="' + $legacy + '" /LOG="' + (Join-Path $testRoot 'setup.log') + '"'
    $p = Start-Process $setup -ArgumentList $arguments -Wait -PassThru
    if ($p.ExitCode -ne 0) { throw "Instalador falhou: $($p.ExitCode)" }
}
InstallYuna
$memory = Join-Path $target 'app\data\memoria-teste.txt'
if (-not (Test-Path -LiteralPath $memory)) { throw 'A migracao das memorias nao funcionou.' }
if (-not (Test-Path -LiteralPath (Join-Path $legacy 'data\memoria-teste.txt'))) { throw 'A origem foi alterada.' }
$env:QT_QPA_PLATFORM = 'offscreen'
$env:YUNA_PERFIL = 'leve'
$app = Start-Process (Join-Path $target 'Yuna.exe') -ArgumentList '--smoke-test' -PassThru
if (-not $app.WaitForExit(120000)) { $app.Kill(); throw 'O aplicativo instalado nao encerrou o teste.' }
if ($app.ExitCode -ne 0) {
    Get-Content (Join-Path $target 'app\data\yuna_startup_error.txt') -ErrorAction SilentlyContinue
    throw 'O aplicativo instalado nao abriu.'
}
$python = Join-Path $target 'runtime\python.exe'
& $python -X utf8 -c 'from pathlib import Path; import app_tools; print(app_tools.configure_shortcuts(Path(app_tools.__file__).parent, True))'
if ($LASTEXITCODE -ne 0) { throw 'Nao consegui criar atalhos do aplicativo instalado.' }
$shortcutPath = Join-Path ([Environment]::GetFolderPath('Startup')) 'Yuna.app.lnk'
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
if ($shortcut.TargetPath -ne (Join-Path $target 'Yuna.exe') -or $shortcut.Arguments -ne '--background') { throw 'Atalho de inicializacao incorreto.' }
& $python -X utf8 -c 'from pathlib import Path; import app_tools; print(app_tools.configure_shortcuts(Path(app_tools.__file__).parent, False))'
if ($LASTEXITCODE -ne 0 -or (Test-Path -LiteralPath $shortcutPath)) { throw 'Nao consegui desativar inicializacao automatica.' }
# Segunda instalacao nao sobrescreve dados criados pelo usuario.
[System.IO.File]::WriteAllText($memory, 'memoria atualizada')
InstallYuna
if ([System.IO.File]::ReadAllText($memory) -ne 'memoria atualizada') { throw 'Atualizacao sobrescreveu a memoria.' }
$uninstall = Start-Process (Join-Path $target 'unins000.exe') -ArgumentList '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART' -Wait -PassThru
if ($uninstall.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $memory)) { throw 'Desinstalacao falhou ou apagou memorias.' }
Write-Host 'Instalacao, aplicativo, migracao, atualizacao e desinstalacao conferidos.'
