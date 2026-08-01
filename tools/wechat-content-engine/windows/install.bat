@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0\.."

echo ========================================
echo AI行动营内容引擎 - Windows 一键安装
echo ========================================

where python >nul 2>nul
if errorlevel 1 (
  echo [错误] 未检测到 Python。请先安装 Python 3.11 或 3.12，并勾选 Add Python to PATH。
  pause
  exit /b 1
)

for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo [信息] Python 版本：%PYVER%

if not exist ".venv\Scripts\python.exe" (
  echo [步骤] 创建虚拟环境...
  python -m venv .venv
  if errorlevel 1 goto :fail
) else (
  echo [跳过] 虚拟环境已存在。
)

echo [步骤] 升级 pip...
.venv\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 goto :fail

echo [步骤] 安装依赖...
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto :fail

if not exist ".env" (
  copy /y ".env.example" ".env" >nul
  echo [完成] 已创建 .env，请用记事本填写 OPENAI_API_KEY 和微信公众号参数。
  start "" notepad ".env"
) else (
  echo [跳过] .env 已存在，不会覆盖。
)

if not exist "output" mkdir output
if not exist "logs" mkdir logs

echo [步骤] 运行基础测试...
.venv\Scripts\python.exe -m pytest -q
if errorlevel 1 (
  echo [警告] 测试未全部通过，请运行 windows\diagnose.bat 查看详情。
) else (
  echo [完成] 自动化测试通过。
)

echo.
echo 安装完成。请保存 .env 后，双击 windows\start.bat 启动。
pause
exit /b 0

:fail
echo.
echo [失败] 安装过程中出现错误。
echo 请运行 windows\diagnose.bat，或查看当前窗口中的报错。
pause
exit /b 1
