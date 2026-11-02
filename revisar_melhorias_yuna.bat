@echo off
chcp 65001 >nul
cd /d "%~dp0"
py -3 -I -B -X utf8 -c "import sys; from pathlib import Path; sys.path.insert(0, str(Path.cwd())); from lab_review import main; raise SystemExit(main())"
pause
