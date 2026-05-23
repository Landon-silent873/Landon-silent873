@echo off
chcp 65001 >nul 2>&1
title SHEIN 自动上架工具 - 安装依赖
setlocal

:: ============================================================
:: Configuration
:: ============================================================
set "SCRIPT_DIR=D:\s-bot"

echo.
echo ============================================================
echo       SHEIN 自动上架工具 - 首次安装
echo ============================================================
echo.

:: ============================================================
:: Check Python
:: ============================================================
echo [步骤 1/3] 检查 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [错误] 未检测到 Python！
    echo.
    echo 请先安装 Python 3.9 或更高版本:
    echo   下载地址: https://www.python.org/downloads/
    echo.
    echo 安装时请勾选 "Add Python to PATH"
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version') do echo [OK] 已检测到 %%i

:: ============================================================
:: Install pip dependencies
:: ============================================================
echo.
echo [步骤 2/3] 安装 Python 依赖包...
echo.
pip install -r "%SCRIPT_DIR%\requirements.txt"
if errorlevel 1 (
    echo.
    echo [错误] pip 依赖安装失败！
    echo [提示] 请检查网络连接，或尝试使用国内镜像:
    echo   pip install -r "%SCRIPT_DIR%\requirements.txt" -i https://pypi.tuna.tsinghua.edu.cn/simple
    echo.
    pause
    exit /b 1
)
echo.
echo [OK] Python 依赖安装完成

:: ============================================================
:: Install Playwright Chromium
:: ============================================================
echo.
echo [步骤 3/3] 安装 Playwright 浏览器引擎...
echo.
playwright install chromium
if errorlevel 1 (
    echo.
    echo [错误] Playwright Chromium 安装失败！
    echo [提示] 请检查网络连接，也可尝试手动运行:
    echo   python -m playwright install chromium
    echo.
    pause
    exit /b 1
)
echo.
echo [OK] Playwright Chromium 安装完成

:: ============================================================
:: Done
:: ============================================================
echo.
echo ============================================================
echo   所有依赖安装完毕！
echo ============================================================
echo.
echo 接下来请:
echo   1. 双击 auto_start.bat 即可一键全自动上架
echo   2. 或双击 start.bat 选择指定品类上架
echo.
echo 首次使用前请确保:
echo   - 已登录 SHEIN 卖家中心
echo   - Chrome 已关闭（脚本会自动启动远程调试模式）
echo.
pause
exit /b 0
