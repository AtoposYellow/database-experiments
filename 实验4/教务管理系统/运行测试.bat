@echo off
chcp 65001 >nul
cd /d %~dp0
title 教务管理系统-功能测试

rem 优先使用项目虚拟环境解释器 .venv，不存在则退回系统 python
set "PY=%~dp0.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

rem MySQL 客户端（用于在数据库端执行建库脚本；建表逻辑不在 Python 中）
set "MYSQL_CLI=mysql"
where mysql >nul 2>nul || set "MYSQL_CLI=D:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe"
if not exist "%MYSQL_CLI%" if "%MYSQL_CLI%" NEQ "mysql" (
  echo 未找到 mysql 客户端，请在 DataGrip 中手动执行 schema.sql 后重试。
  pause
  exit /b 1
)

echo ===== 教务管理系统 功能测试 =====
echo.

rem 1) 环境自检
"%PY%" check_env.py
if errorlevel 1 (
  echo.
  echo 环境检查未通过，请按提示处理后重试。
  pause
  exit /b 1
)

rem 2) 服务未启动则后台启动（最小化窗口）
"%PY%" -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/ping', timeout=2).status==200 else 1)" >nul 2>nul
if errorlevel 1 (
  echo 服务未启动，正在后台启动...
  start "" /min "%PY%" app.py --port 8000
  timeout /t 2 /nobreak >nul
)

rem 3) 恢复初始数据：由 MySQL 客户端执行 schema.sql（建库建表在数据库端）
echo.
echo [1/3] 恢复初始示例数据（MySQL 端执行 schema.sql）...
"%MYSQL_CLI%" -u root -proot --default-character-set=utf8mb4 < schema.sql
if errorlevel 1 (
  echo 自动恢复失败：请在 DataGrip 中执行 schema.sql 后重试。
  pause
  exit /b 1
)

rem 4) 跑两套测试
echo.
echo [2/3] API 集成测试（七大功能 + 失败用例）...
"%PY%" test_api.py
if errorlevel 1 (echo API 测试存在失败项！ & pause & exit /b 1)

echo.
echo [3/3] 数据库完整性约束测试...
"%PY%" test_constraints.py
if errorlevel 1 (echo 约束测试存在失败项！ & pause & exit /b 1)

rem 5) 测试会改动数据，结束后恢复初始状态
echo.
echo 全部通过。按任意键恢复初始示例数据并退出...
pause >nul
"%MYSQL_CLI%" -u root -proot --default-character-set=utf8mb4 < schema.sql >nul 2>nul
echo 已恢复初始数据。测试结束。
pause
