@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Instala o ditado e a escuta local opcional. O modelo Whisper pode ser baixado no primeiro uso.
py -3 -m pip install -r "%~dp0requirements-voz.txt"
pause
