@echo off
chcp 65001 >nul
cd /d "%~dp0"
py -3 development_lab.py
pause
