@echo off
REM 旅途管家后端 - 本机一键启动（双击运行）
REM 后端监听 0.0.0.0:8000（允许本机与局域网/真机预览访问）
cd /d "%~dp0"
"C:\Users\dell\.workbuddy\binaries\python\envs\default\Scripts\python.exe" -m uvicorn main:app --host 0.0.0.0 --port 8000
pause
