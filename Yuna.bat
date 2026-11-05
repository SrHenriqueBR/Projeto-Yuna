@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\iniciar.ps1"
if errorlevel 1 (
    echo Nao consegui preparar a Yuna. Confira a mensagem acima.
    pause
    exit /b 1
)
exit /b 0
