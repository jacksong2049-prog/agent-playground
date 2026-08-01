@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0\..\..\.."

echo ========================================
echo AI行动营内容引擎 - 更新程序
echo ========================================

where git >nul 2>nul
if errorlevel 1 (
  echo [错误] 未检测到 Git。
  pause
  exit /b 1
)

git status --porcelain > "%TEMP%\wechat-engine-status.txt"
for %%A in ("%TEMP%\wechat-engine-status.txt") do if %%~zA gtr 0 (
  echo [错误] 当前仓库存在未提交修改，为避免覆盖，已停止更新。
  type "%TEMP%\wechat-engine-status.txt"
  pause
  exit /b 1
)

git fetch origin
if errorlevel 1 goto :fail

git checkout feat/wechat-content-engine-mvp
if errorlevel 1 goto :fail

git pull --ff-only origin feat/wechat-content-engine-mvp
if errorlevel 1 goto :fail

cd /d "%~dp0\.."
if exist ".venv\Scripts\python.exe" (
  .venv\Scripts\python.exe -m pip install -r requirements.txt
  .venv\Scripts\python.exe -m pytest -q
) else (
  echo [提示] 尚未创建虚拟环境，请运行 windows\install.bat。
)

echo 更新完成。
pause
exit /b 0

:fail
echo [失败] 更新没有完成，请检查网络、Git 分支或仓库状态。
pause
exit /b 1
