@echo off
setlocal EnableExtensions
chcp 65001 >nul

echo 正在停止本机 8000 端口上的内容引擎...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
  taskkill /PID %%p /F >nul 2>nul
  if not errorlevel 1 echo 已停止进程 %%p。
)

echo 停止操作完成。
pause
