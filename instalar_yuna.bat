@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist "%~dp0instalar_yuna.ps1" (
    echo Falta instalar_yuna.ps1. Atualize todos os arquivos.
    pause
    exit /b 1
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0instalar_yuna.ps1"
set "yuna_exit=%errorlevel%"
if not "%yuna_exit%"=="0" echo O instalador informou um erro. Leia as mensagens acima.
pause
exit /b %yuna_exit%
