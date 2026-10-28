<#
Yuna 0.26: assistente de instalação/diagnóstico para Windows.
Não instala Python/Ollama automaticamente, não exige administrador, não apaga dados.
Pip e Ollama pull somente após confirmação explícita. Não altera PATH global.
#>
param([switch]$Diagnostico)

# Native commands such as pip return exit codes; we verify those explicitly.
# Do not treat their stderr progress/warnings as terminating exceptions on PS 5.1.
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $Root

function Info([string]$message) { Write-Host "[Yuna] $message" -ForegroundColor Cyan }
function Warn([string]$message) { Write-Host "[!] $message" -ForegroundColor Yellow }
function AskYes([string]$question) {
    $answer = Read-Host "$question [s/N]"
    return $answer -match '^(s|sim)$'
}
function ReadRamGb {
    try {
        $ram = (Get-CimInstance -ClassName Win32_ComputerSystem -ErrorAction Stop).TotalPhysicalMemory
        if ($ram -gt 0) { return [Math]::Round($ram / 1GB, 1) }
    } catch {
        Warn "Nao consegui consultar a RAM; isso nao impede a instalacao."
    }
    return 0.0
}
function HasPython {
    if (-not (Get-Command py -ErrorAction SilentlyContinue)) { return $false }
    & py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" *> $null
    return $LASTEXITCODE -eq 0
}
function HasLibraries {
    & py -3 -c "import PySide6, docx, openpyxl, pptx, pypdf, reportlab" *> $null
    return $LASTEXITCODE -eq 0
}
function GetSavedModel {
    $config = Join-Path $Root "data\modelo_yuna.txt"
    if (Test-Path -LiteralPath $config) {
        try {
            $value = ([System.IO.File]::ReadAllText($config, [System.Text.Encoding]::UTF8)).Trim([char]0xFEFF).Trim()
            if ($value -in @("qwen2.5:1.5b", "qwen2.5:3b")) { return $value }
        } catch { }
    }
    return "qwen2.5:3b"
}

Write-Host ""
Info "Projeto Yuna 0.26 - Instalacao e diagnostico"
Write-Host "Pasta: $Root"
$ram = ReadRamGb
if ($ram -gt 0) {
    Info "Memoria RAM: $ram GB"
    if ($ram -le 8.5) { Info "Para esta RAM, recomendamos qwen2.5:1.5b (mais leve)." }
}
if (-not (HasPython)) {
    Warn "Python 3.10+ com o comando py nao foi localizado."
    Write-Host "Instale o Python 3.12 (64 bits) com Python Launcher:"
    Write-Host "https://www.python.org/downloads/windows/"
    Write-Host "Feche e reabra o terminal apos instalar."
    exit 1
}
$pythonVersion = & py -3 -c "import sys; print(sys.version.split()[0])"
Info "Python detectado: $pythonVersion"

$libsOK = HasLibraries
if ($libsOK) { Info "Bibliotecas do menu e documentos: OK" }
else { Warn "Bibliotecas do menu e documentos: ausentes ou incompletas" }

$ollamaCmd = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $ollamaCmd) {
    Warn "Ollama nao foi encontrado no PATH."
    Write-Host "Instale e abra o Ollama a partir de: https://ollama.com/download/windows"
    if ($Diagnostico) { exit 1 }
    Write-Host "Depois reabra este instalador para baixar o modelo."
    exit 1
}
$installedModels = (& ollama list 2>&1 | Out-String)
if ($LASTEXITCODE -ne 0) {
    Warn "Ollama esta instalado, mas nao respondeu."
    Write-Host "Abra o Ollama; se necessario execute 'ollama serve' em outro terminal."
    exit 1
}
Info "Ollama local: OK"
$saved = GetSavedModel
Info "Modelo configurado: $saved (YUNA_MODEL no ambiente tem prioridade)"

if ($Diagnostico) {
    Write-Host ""
    Write-Host "=== DIAGNOSTICO (somente leitura) ==="
    if (-not $libsOK) {
        Warn "Para reparar: py -3 -m pip install -r requirements-mascote.txt"
    }
    if ([regex]::IsMatch($installedModels, "(?m)^\s*$([regex]::Escape($saved))\s+")) {
        Info "Modelo configurado presente no Ollama."
    } else {
        Warn "Modelo configurado ausente. Instale com: ollama pull $saved"
    }
    Write-Host "Esta verificacao nao alterou nenhum arquivo ou programa."
    exit 0
}

if (-not $libsOK) {
    Write-Host ""
    if (-not (AskYes "Deseja instalar as bibliotecas Python de requirements-mascote.txt?")) {
        Warn "Instalacao cancelada. Nenhum pacote foi instalado."
        exit 1
    }
    & py -3 -m pip install -r (Join-Path $Root "requirements-mascote.txt")
    if ($LASTEXITCODE -ne 0 -or -not (HasLibraries)) {
        Warn "Nao foi possivel instalar ou importar todas as bibliotecas."
        Write-Host "Veja o erro acima; verifique sua versao do Python e a conexao."
        exit 1
    }
    Info "Bibliotecas instaladas."
}

Write-Host ""
Info "Escolha o modelo de texto local:"
Write-Host "1 - qwen2.5:1.5b (mais leve, recomendado para ate 8 GB de RAM)"
Write-Host "2 - qwen2.5:3b (respostas potencialmente melhores, mais memoria)"
$defaultChoice = "2"
if ($ram -gt 0 -and $ram -le 8.5) { $defaultChoice = "1" }
if ($saved -eq "qwen2.5:1.5b") { $defaultChoice = "1" }
$choice = Read-Host "Digite 1 ou 2 (Enter = $defaultChoice)"
if ([string]::IsNullOrWhiteSpace($choice)) { $choice = $defaultChoice }
switch ($choice) {
    "1" { $model = "qwen2.5:1.5b" }
    "2" { $model = "qwen2.5:3b" }
    default {
        Warn "Opcao invalida. Nada foi alterado no modelo."
        exit 1
    }
}
if (-not [regex]::IsMatch($installedModels, "(?m)^\s*$([regex]::Escape($model))\s+")) {
    if (-not (AskYes "O modelo $model nao esta instalado. Baixar pelo Ollama agora?")) {
        Warn "Modelo nao baixado; configuracao atual preservada."
        exit 1
    }
    & ollama pull $model
    if ($LASTEXITCODE -ne 0) {
        Warn "Download do modelo nao foi concluido. Configuracao anterior preservada."
        exit 1
    }
}
# Somente apos dependencia/modelo conferidos persiste a selecao, sem tocar no banco.
& py -3 -c "import sys; from model_config import save_selected_model; save_selected_model('.', sys.argv[1])" $model
if ($LASTEXITCODE -ne 0) {
    Warn "Nao consegui salvar a selecao do modelo."
    exit 1
}
Info "Modelo pronto: $model"

if (AskYes "Criar um atalho da Yuna na Area de Trabalho?") {
    try {
        $desktop = [Environment]::GetFolderPath("DesktopDirectory")
        $shortcut = (New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $desktop "Yuna.lnk"))
        $shortcut.TargetPath = Join-Path $Root "iniciar_yuna.bat"
        $shortcut.WorkingDirectory = $Root
        $shortcut.Description = "Projeto Yuna - assistente local"
        $shortcut.Save()
        Info "Atalho Yuna criado para este usuario."
    } catch {
        Warn "Nao consegui criar atalho: $($_.Exception.Message)"
    }
}

Write-Host ""
Info "Instalacao concluida. Seus arquivos pessoais em data/ nao foram apagados."
if (AskYes "Deseja abrir a Yuna agora?") {
    Start-Process -FilePath (Join-Path $Root "iniciar_yuna.bat") -WorkingDirectory $Root
}
exit 0
