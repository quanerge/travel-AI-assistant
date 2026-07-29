@echo off
setlocal
set ROOT=%~dp0
set ADMIN=%ROOT%admin
set SERVER=%ROOT%server

echo [0/3] Stopping any OLD backend still on port 8000 (fixes enc: ciphertext bug) ...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr /R ":8000 " ^| findstr "LISTENING"') do (
  taskkill /F /PID %%a >nul 2>&1
)
timeout /t 2 /nobreak >nul

echo [1/3] Building admin frontend (npm install + npm run build)
cd /d "%ADMIN%"
call npm install
if errorlevel 1 (
  echo ERROR: npm install failed
  pause
  exit /b 1
)
call npm run build
if errorlevel 1 (
  echo ERROR: npm run build failed
  pause
  exit /b 1
)
echo Admin build complete: %ADMIN%\dist

echo [2/3] Starting backend (FastAPI on port 8000, serves /ui)
cd /d "%SERVER%"
python migrate_phones.py
start "travel-backend" cmd /k "python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
echo Backend starting at http://127.0.0.1:8000

echo [3/3] Done. Opening admin UI ...
timeout /t 5 /nobreak >nul
start http://127.0.0.1:8000/ui/
echo   Admin UI :  http://127.0.0.1:8000/ui/
echo   API docs :  http://127.0.0.1:8000/docs
echo   Mini-program:  import %ROOT%miniprogram in WeChat DevTools
echo   WeChat release needs HTTPS + ICP-filed domain + request domain whitelist
echo.
pause
