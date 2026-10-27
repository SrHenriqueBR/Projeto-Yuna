@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist "yuna_avatar.py" (
    echo Falta yuna_avatar.py. Copie todos os arquivos da versao nova.
    pause
    exit /b 1
)
if not exist "avatar_state.py" (
    echo Falta avatar_state.py.
    pause
    exit /b 1
)
py -3 -c "import PySide6" >nul 2>nul
if errorlevel 1 (
    echo Instale: py -3 -m pip install -r requirements-mascote.txt
    pause
    exit /b 1
)
where pyw >nul 2>nul
if errorlevel 1 (
    echo Nao encontrei pyw. Verifique o Python Launcher.
    pause
    exit /b 1
)
start "" pyw -3 "%~dp0yuna_avatar.py"
exit /b 0
