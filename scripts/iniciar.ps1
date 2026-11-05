param([switch]$SomentePreparar)
$ErrorActionPreference = 'Stop'
$rootPath = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $rootPath
Add-Type -AssemblyName System.Windows.Forms
try {
    $python = Join-Path $rootPath '.venv\Scripts\python.exe'
    $ready = $false
    if (Test-Path -LiteralPath $python) {
        & $python -c 'import PySide6, docx, openpyxl, pptx, pypdf, reportlab, sounddevice, faster_whisper' *> $null
        $ready = $LASTEXITCODE -eq 0
    }
    if (-not $ready) {
        $question = 'Preparar a Yuna nesta pasta? Vou criar um ambiente privado e baixar as bibliotecas de interface, documentos e voz. Pode usar internet e disco. Para instalar sem configurar Python, prefira Yuna-Setup.exe em Releases.'
        $answer = [System.Windows.Forms.MessageBox]::Show($question, 'Yuna - preparar aplicativo', 'YesNo', 'Information')
        if ($answer -ne 'Yes') { exit 0 }
        if (-not (Test-Path -LiteralPath $python)) {
            $launcher = Get-Command py -ErrorAction SilentlyContinue
            if ($launcher) {
                & $launcher.Source -3 -m venv (Join-Path $rootPath '.venv')
            } else {
                $launcher = Get-Command python -ErrorAction SilentlyContinue
                if (-not $launcher) {
                    Start-Process 'https://github.com/SrHenriqueBR/Projeto-Yuna/releases/latest'
                    throw 'Python nao encontrado. Baixe Yuna-Setup.exe na pagina aberta.'
                }
                & $launcher.Source -m venv (Join-Path $rootPath '.venv')
            }
            if ($LASTEXITCODE -ne 0) { throw 'Nao consegui criar o ambiente da Yuna.' }
        }
        & $python -m pip install --disable-pip-version-check -r (Join-Path $rootPath 'requirements-mascote.txt') -r (Join-Path $rootPath 'requirements-voz.txt')
        if ($LASTEXITCODE -ne 0) { throw 'Preparacao incompleta. Confira a conexao ou use Yuna-Setup.exe.' }
        & $python -c 'import PySide6, docx, openpyxl, pptx, pypdf, reportlab, sounddevice, faster_whisper'
        if ($LASTEXITCODE -ne 0) { throw 'Uma biblioteca nao iniciou. Use o instalador para obter o ambiente completo.' }
    }
    if (-not $SomentePreparar) {
        $pythonw = Join-Path $rootPath '.venv\Scripts\pythonw.exe'
        Start-Process -FilePath $pythonw -ArgumentList @(('"' + (Join-Path $rootPath 'yuna_launcher.py') + '"'), '--compact') -WorkingDirectory $rootPath
    }
} catch {
    [System.Windows.Forms.MessageBox]::Show($_.Exception.Message, 'Yuna - preparacao', 'OK', 'Error') | Out-Null
    Write-Error $_.Exception.Message
    exit 1
}
