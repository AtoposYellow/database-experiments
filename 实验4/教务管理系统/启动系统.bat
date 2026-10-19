@echo off
chcp 65001 >nul
cd /d %~dp0
title 教务管理系统

rem 优先使用项目虚拟环境解释器 .venv，不存在则退回系统 python
set "PY=%~dp0.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

"%PY%" check_env.py
if errorlevel 1 (
  echo.
  echo 环境检查未通过，请按上面的提示处理后重试。
  pause
  exit /b 1
)
echo.
echo 环境就绪，正在启动服务（关闭本窗口即停止服务）...
start "" /min cmd /c "timeout /t 2 /nobreak >nul & start http://127.0.0.1:8000"
"%PY%" app.py
pause
