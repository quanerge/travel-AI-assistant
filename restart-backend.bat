@echo off
setlocal
set SERVER=%~dp0server

echo Stopping any OLD backend still on port 8000 (fixes enc: ciphertext bug) ...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr /R ":8000 " ^| findstr "LISTENING"') do (
  taskkill /F /PID %%a >nul 2>&1
)
timeout /t 2 /nobreak >nul

cd /d "%SERVER%"
python migrate_phones.py
start "travel-backend" cmd /k "python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
echo Backend restarted. Opening admin UI ...
timeout /t 5 /nobreak >nul
start http://127.0.0.1:8000/ui/
echo   Admin UI :  http://127.0.0.1:8000/ui/
echo   API docs :  http://127.0.0.1:8000/docs
echo.
pause
