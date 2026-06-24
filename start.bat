@echo off
echo ==========================================
echo   RAgent Router v0.1.0
echo ==========================================
echo.
echo Choose launch mode:
echo   [1] Browser  (http://localhost:5173^)
echo   [2] Desktop  (Electron window^)
echo.
set /p choice="Enter 1 or 2: "

set PYTHON=C:\Users\songjunkui\AppData\Local\Programs\Python\Python314\python.exe

echo.
echo Starting backend...
start "RAgent-Backend" cmd /c "cd /d %~dp0backend && %PYTHON% -m uvicorn main:app --host 0.0.0.0 --port 8000"
echo Backend starting on http://localhost:8000

if "%choice%"=="2" goto desktop

:browser
echo Starting frontend (Browser)...
timeout /t 3 /nobreak >nul
cd /d %~dp0frontend
npx vite --host
goto end

:desktop
echo Starting frontend (Electron Desktop)...
echo Waiting for backend + Vite dev server...
timeout /t 3 /nobreak >nul
cd /d %~dp0frontend
npm run electron:dev
goto end

:end
pause
