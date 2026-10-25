@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist "office_agent.py" (
    echo Falta office_agent.py. Atualize todos os arquivos da Yuna.
    pause
    exit /b 1
)
if not exist "web_actions.py" (
    echo Falta web_actions.py. Atualize todos os arquivos da Yuna.
    pause
    exit /b 1
)
if not exist "screen_consent.py" (
    echo Falta screen_consent.py. Atualize todos os arquivos da Yuna.
    pause
    exit /b 1
)
if not exist "document_writer.py" (
    echo Falta document_writer.py. Copie todos os arquivos atualizados da Yuna.
    pause
    exit /b 1
)
if not exist "diary.py" (
    echo Falta diary.py. Atualize os arquivos do projeto antes de abrir a mascote.
    pause
    exit /b 1
)
if not exist "yuna_overlay.py" (
    echo Falta yuna_overlay.py. Atualize todos os arquivos da Yuna.
    pause
    exit /b 1
)
where py >nul 2>nul
if errorlevel 1 (
    echo Instale Python 3.10 ou superior com Python Launcher.
    pause
    exit /b 1
)
py -3 -c "import PySide6" >nul 2>nul
if errorlevel 1 (
    echo Instale a interface: py -3 -m pip install PySide6
    echo Para voz online opcional: py -3 -m pip install edge-tts
    pause
    exit /b 1
)
py -3 yuna_overlay.py
if errorlevel 1 pause
