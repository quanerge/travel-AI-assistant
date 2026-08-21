@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo  Cloudflare Quick Tunnel  ->  http://localhost:8000
echo  用途：让手机脱离局域网也能真机调试小程序后端
echo  说明：每次启动都会生成新的随机 *.trycloudflare.com 地址
echo        地址出现后，复制到 miniprogram/utils/config.js 的 baseUrl
echo        （结尾带 /api），并在手机端保持「开发调试/不校验合法域名」
echo  关闭本窗口即停止隧道
echo ============================================
echo.
cloudflared.exe tunnel --url http://localhost:8000
pause
