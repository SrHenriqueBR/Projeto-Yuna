@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist "yuna_launcher.py" (
    echo Falta yuna_launcher.py. Atualize todos os arquivos do menu.
    pause
    exit /b 1
)
if not exist "yuna_desktop.py" (
    echo A interface grafica da Yuna nao foi encontrada. Atualize todos os arquivos.
    pause
    exit /b 1
)
if not exist "document_library.py" (
    echo Falta document_library.py. Atualize os arquivos .py do projeto.
    pause
    exit /b 1
)
where pyw >nul 2>nul
if errorlevel 1 (
    echo O launcher grafico pyw nao foi encontrado. Instale o Python Launcher.
    pause
    exit /b 1
)
py -3 -c "import PySide6, docx, openpyxl, pptx, pypdf" >nul 2>nul
if errorlevel 1 (
    echo A Yuna precisa das bibliotecas do menu e dos documentos.
    echo Execute: py -3 -m pip install -r requirements-mascote.txt
    pause
    exit /b 1
)
start "" pyw -3 "%~dp0yuna_launcher.py"
exit /b 0
