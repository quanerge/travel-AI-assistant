@echo off
REM ============================================================
REM  One-click launcher: backend (FastAPI :8000) + admin dev (:5173)
REM  Each service opens in its OWN window. Close that window to stop it.
REM  Requires: server venv ready + admin node_modules present.
REM  NOTE: admin (Vite) proxies /api and /static to the backend on :8000,
REM        so keep the backend window open while using admin.
REM ============================================================

cd /d "%~dp0server"
start "lvguanjia-backend-8000" cmd /k "C:\Users\dell\.workbuddy\binaries\python\envs\default\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000"

timeout /t 2 /nobreak >nul

cd /d "%~dp0admin"
start "lvguanjia-admin-5173" cmd /k "npm run dev"

echo.
echo ===================================================
echo  Both services are starting...
echo   Backend : http://localhost:8000  (window: lvguanjia-backend-8000)
echo   Admin   : http://localhost:5173  (window: lvguanjia-admin-5173)
echo  If a port shows "address already in use", another instance
echo  is already running -- just close that new window, or stop the
echo  old one first. Keep the backend window open for admin to work.
echo ===================================================
