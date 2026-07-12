@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0\.."

if not exist "logs" mkdir logs
set REPORT=logs\diagnose-%DATE:~0,4%%DATE:~5,2%%DATE:~8,2%-%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%.txt
set REPORT=%REPORT: =0%

echo AI行动营内容引擎诊断报告 > "%REPORT%"
echo 生成时间：%DATE% %TIME% >> "%REPORT%"
echo ======================================== >> "%REPORT%"

echo [1] 系统信息 >> "%REPORT%"
ver >> "%REPORT%" 2>&1
where python >> "%REPORT%" 2>&1
python --version >> "%REPORT%" 2>&1
where git >> "%REPORT%" 2>&1
git --version >> "%REPORT%" 2>&1

echo.>> "%REPORT%"
echo [2] 文件检查 >> "%REPORT%"
for %%F in (.env requirements.txt app.py content_engine.py audit_tools.py wechat_media.py) do (
  if exist "%%F" (echo OK %%F>> "%REPORT%") else (echo MISSING %%F>> "%REPORT%")
)
if exist ".venv\Scripts\python.exe" (echo OK .venv>> "%REPORT%") else (echo MISSING .venv>> "%REPORT%")

echo.>> "%REPORT%"
echo [3] 环境变量状态（不输出密钥） >> "%REPORT%"
if exist ".env" (
  findstr /b "OPENAI_API_KEY=" .env | findstr /v "OPENAI_API_KEY=$" >nul && (echo OPENAI_API_KEY=已填写>> "%REPORT%") || (echo OPENAI_API_KEY=未填写>> "%REPORT%")
  findstr /b "WECHAT_APP_ID=" .env | findstr /v "WECHAT_APP_ID=$" >nul && (echo WECHAT_APP_ID=已填写>> "%REPORT%") || (echo WECHAT_APP_ID=未填写>> "%REPORT%")
  findstr /b "WECHAT_APP_SECRET=" .env | findstr /v "WECHAT_APP_SECRET=$" >nul && (echo WECHAT_APP_SECRET=已填写>> "%REPORT%") || (echo WECHAT_APP_SECRET=未填写>> "%REPORT%")
) else (
  echo .env 不存在>> "%REPORT%"
)

echo.>> "%REPORT%"
echo [4] 端口检查 >> "%REPORT%"
netstat -ano | findstr ":8000" >> "%REPORT%" 2>&1

echo.>> "%REPORT%"
echo [5] Python 导入与测试 >> "%REPORT%"
if exist ".venv\Scripts\python.exe" (
  .venv\Scripts\python.exe -c "import fastapi,uvicorn,openai,httpx,feedparser; print('依赖导入正常')" >> "%REPORT%" 2>&1
  .venv\Scripts\python.exe -m pytest -q >> "%REPORT%" 2>&1
) else (
  echo 未创建虚拟环境，跳过 Python 测试。>> "%REPORT%"
)

echo.>> "%REPORT%"
echo [6] Git 状态 >> "%REPORT%"
git status --short >> "%REPORT%" 2>&1
git branch --show-current >> "%REPORT%" 2>&1

echo 诊断完成：%CD%\%REPORT%
start "" notepad "%REPORT%"
pause
