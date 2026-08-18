@echo off
REM Start the admin (Vue3 + Vite) dev server. Double-click to run.
REM Default URL: http://localhost:5173  (requires backend on port 8000)
cd /d "%~dp0admin"
if not exist node_modules (
  echo Dependencies missing, running npm install ...
  call npm install
)
echo.
echo Admin dev server starting at http://localhost:5173
echo Make sure the FastAPI backend is running on port 8000
echo.
call npm run dev
