@echo off
chcp 65001 >nul
cd /d "%~dp0"
py -3 development_lab.py --autoteste
if errorlevel 1 echo O autoteste não passou. Confira a mensagem acima.
pause
