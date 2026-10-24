@echo off
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
    echo Instale o Python 3.10 ou superior com o Python Launcher.
    pause
    exit /b 1
)
py -3 yuna.py
pause
