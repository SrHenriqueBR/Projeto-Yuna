@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
    echo Instale o Python com o Python Launcher e tente novamente.
    pause
    exit /b 1
)
if not exist "yuna_web.py" (
    echo Atualize todos os arquivos do projeto e a pasta docs.
    pause
    exit /b 1
)
echo Abrindo Yuna Web. O chat utiliza o Ollama instalado neste computador.
echo Mantenha esta janela aberta durante a conversa.
py -3 yuna_web.py
if errorlevel 1 pause
