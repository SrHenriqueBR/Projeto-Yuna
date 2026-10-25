@echo off
chcp 65001 >nul
rem Usa um modelo local maior, opcional. Instale antes: ollama pull qwen2.5:7b
set "YUNA_MODEL=qwen2.5:7b"
call "%~dp0iniciar_yuna_mascote.bat"
