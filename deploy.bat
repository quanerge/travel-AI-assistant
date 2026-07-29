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

REM ============================================================
REM 微信客服消息回传管理后台（可选，生产启用）
REM ------------------------------------------------------------
REM 1. 公众平台「功能 -> 客服 -> 消息推送」启用，填写：
REM      服务器地址(URL): https://你的域名/api/wechat/callback
REM                        (nginx 已把 /api 反代到后端 /wechat/callback；
REM                         若直连后端则用 https://公网IP:8000/wechat/callback)
REM      Token           : 与后端环境变量 WECHAT_CALLBACK_TOKEN 一致
REM                        (默认 lvguanjia_callback)
REM      消息加解密方式  : 选「明文模式」
REM                        (本项目 requirements 不引入 cryptography，不支持 AES 解密)
REM 2. 确保已配置环境变量 WECHAT_APPID / WECHAT_SECRET
REM      (回复下发复用订阅消息的同一套凭证)
REM 3. 重启后端后，管理后台左侧「客服消息」即可看到客户会话并回复
REM 注意：本地/内网收不到微信回调，需公网可达（Docker 生产或内网穿透）
REM ============================================================
echo   See README.md "六、微信客服消息回传管理后台（生产部署）" for full steps.
echo.
pause
