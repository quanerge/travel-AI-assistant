@echo off
REM 用微信开发者工具 CLI 打开小程序项目（自动探测 cli 路径）
REM 注意：本机 WorkBuddy 注入了 NODE_OPTIONS，会导致微信自带 node 报错，这里先清除。
set NODE_OPTIONS=
set PROJ=D:\github\旅游AI小助手\miniprogram

set CLI=
if exist "C:\Program Files (x86)\Tencent\微信web开发者工具\cli.bat" set CLI="C:\Program Files (x86)\Tencent\微信web开发者工具\cli.bat"
if not defined CLI if exist "C:\Program Files\Tencent\微信web开发者工具\cli.bat" set CLI="C:\Program Files\Tencent\微信web开发者工具\cli.bat"
if not defined CLI if exist "%LOCALAPPDATA%\Programs\微信开发者工具\cli.bat" set CLI="%LOCALAPPDATA%\Programs\微信开发者工具\cli.bat"
if not defined CLI if exist "%LOCALAPPDATA%\微信web开发者工具\cli.bat" set CLI="%LOCALAPPDATA%\微信web开发者工具\cli.bat"

if not defined CLI (
  echo 未找到微信开发者工具，请先安装：
  echo   https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html
  echo 安装完成后重新运行本脚本即可。
  pause
  exit /b 1
)

REM 若报 "服务端口" 错误，请先在 IDE 内：设置 -^> 安全 -^> 开启服务端口，并重启 IDE。
%CLI% -o "%PROJ%"
pause
