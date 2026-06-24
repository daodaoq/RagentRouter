@echo off
echo ==========================================
echo   RAgent Router - Starting...
echo ==========================================
echo.

REM Use Python 3.14 from the installed location
set PYTHON=C:\Users\songjunkui\AppData\Local\Programs\Python\Python314\python.exe

echo [1/2] Starting backend (FastAPI) on port 8000...
start "RAgent-Backend" cmd /c "cd /d %~dp0backend && %PYTHON% -m uvicorn main:app --host 0.0.0.0 --port 8000"

echo [2/2] Starting frontend (Vite) on port 5173...
start "RAgent-Frontend" cmd /c "cd /d %~dp0frontend && npx vite --host"

echo.
echo ==========================================
echo   Backend:  http://localhost:8000/docs
echo   Frontend: http://localhost:5173
echo ==========================================
echo.
echo Close this window or press Ctrl+C in each window to stop.
pause
