@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0\.."

if not exist ".venv\Scripts\python.exe" (
  echo [错误] 尚未安装，请先双击 windows\install.bat。
  pause
  exit /b 1
)
if not exist ".env" (
  echo [错误] 未找到 .env，请先运行安装脚本。
  pause
  exit /b 1
)

if not exist "logs" mkdir logs

echo 正在启动 AI行动营内容引擎...
start "AI行动营内容引擎" cmd /k "cd /d "%CD%" && .venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000"

timeout /t 3 /nobreak >nul
start "" "http://127.0.0.1:8000"

echo 已启动：http://127.0.0.1:8000
echo 请勿关闭新打开的服务窗口；停止时双击 windows\stop.bat。
exit /b 0
