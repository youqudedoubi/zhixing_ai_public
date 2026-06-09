@echo off
title Zhixing AI - Starting...

echo ================================
echo   Zhixing AI v1.0 Launcher
echo ================================
echo.

set ROOT=%~dp0
set PYTHON=python

echo [1/2] Starting backend (FastAPI)...
start "ZhixingAI-Backend" cmd /k "cd /d "%ROOT%" && "%PYTHON%" -m uvicorn code.backend.main:app --host 127.0.0.1 --port 8000 --reload"

echo [2/2] Starting frontend (Vite)...
start "ZhixingAI-Frontend" cmd /k "cd /d "%ROOT%code\frontend%" && npm run dev"

echo.
echo ================================
echo   Backend:  http://127.0.0.1:8000
echo   Frontend: http://127.0.0.1:5173
echo ================================
echo.
echo Press any key to close this window...
pause >nul
