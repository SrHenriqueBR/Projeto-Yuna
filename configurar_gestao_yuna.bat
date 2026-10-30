@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
    echo Instale o Python com o Python Launcher.
    pause
    exit /b 1
)
py -3 yuna_governance.py --configurar-proprietario
pause
