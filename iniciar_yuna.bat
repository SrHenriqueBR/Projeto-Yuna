@echo off
cd /d "%~dp0"
for %%F in (yuna.py computer.py desktop.py local_agent.py) do (
    if not exist "%%F" (
        echo Falta %%F. Copie todos os arquivos .py da pasta nova para esta pasta.
        echo Preserve a pasta data com suas memorias.
        pause
        exit /b 1
    )
)
where py >nul 2>nul
if errorlevel 1 (
    echo Instale o Python 3.10 ou superior com o Python Launcher.
    pause
    exit /b 1
)
py -3 yuna.py
pause
