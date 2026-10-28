@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist "%~dp0instalar_yuna.ps1" (
    echo Falta instalar_yuna.ps1. Atualize todos os arquivos.
    pause
    exit /b 1
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0instalar_yuna.ps1" -Diagnostico
set "yuna_exit=%errorlevel%"
pause
exit /b %yuna_exit%
