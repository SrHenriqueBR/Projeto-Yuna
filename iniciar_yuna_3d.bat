@echo off
setlocal
cd /d "%~dp0avatar3d" || (
    echo Nao foi possivel encontrar a pasta avatar3d.
    pause
    exit /b 1
)
where node >nul 2>&1
if errorlevel 1 (
    echo O avatar 3D precisa de Node.js 22 LTS instalado.
    echo Instale a partir de https://nodejs.org/ e abra novamente.
    pause
    exit /b 1
)
where npm >nul 2>&1
if errorlevel 1 (
    echo npm nao encontrado. Verifique a instalacao do Node.js.
    pause
    exit /b 1
)
if not exist "node_modules\vite\bin\vite.js" (
    echo O avatar 3D ainda nao foi instalado.
    echo Abra um terminal nesta pasta e execute: npm install
    echo O avatar 2D continua funcionando sem estas dependencias.
    pause
    exit /b 1
)
echo.
echo YUNA 3D - prototipo VRM opcional
echo Acesso local: http://127.0.0.1:5173
echo Para encerrar, pressione Ctrl+C nesta janela.
echo.
start "" /MIN powershell.exe -NoProfile -Command "Start-Sleep -Seconds 4; Start-Process 'http://127.0.0.1:5173'"
call npm run dev -- --strictPort
if errorlevel 1 (
    echo O servidor 3D nao iniciou. Confira se a porta 5173 esta disponivel.
    pause
)
