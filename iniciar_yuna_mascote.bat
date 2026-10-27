@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist "agent_brain.py" (
    echo Falta agent_brain.py. Atualize os arquivos do projeto para Yuna 0.13.
    pause
    exit /b 1
)
if not exist "file_diagnostics.py" (
    echo Falta file_diagnostics.py. Atualize todos os arquivos Python da Yuna.
    pause
    exit /b 1
)
if not exist "free_apis.py" (
    echo Falta free_apis.py. Atualize todos os arquivos Python para Yuna 0.16.
    pause
    exit /b 1
)
if not exist "integrations.py" (
    echo Falta integrations.py. Atualize todos os arquivos para Yuna 0.15.
    pause
    exit /b 1
)
if not exist "proactive.py" (
    echo Falta proactive.py. Atualize todos os arquivos Python da Yuna.
    pause
    exit /b 1
)
if not exist "own_initiative.py" (
    echo Falta own_initiative.py. Atualize todos os arquivos da Yuna.
    pause
    exit /b 1
)
if not exist "language_quality.py" (
    echo Falta language_quality.py. Atualize todos os arquivos da Yuna.
    pause
    exit /b 1
)
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
