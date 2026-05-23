@echo off
chcp 65001 >nul 2>&1
title SHEIN 全自动上架
setlocal enabledelayedexpansion

:: ============================================================
:: Configuration
:: ============================================================
set "SCRIPT_DIR=D:\s-bot"
set "IMAGE_DIR=D:\A今日上架"
set "CHROME_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe"
set "CDP_PORT=9222"
set "BASE_PRODUCT_ID_TSHIRT=SPMPA4202605222803370"
set "BASE_PRODUCT_ID_HOODIE=SPMPA4202605222803370"

echo.
echo ============================================================
echo          SHEIN 全自动上架 - 一键启动
echo ============================================================
echo.
echo [信息] 脚本路径: %SCRIPT_DIR%
echo [信息] 图片路径: %IMAGE_DIR%
echo.

:: ============================================================
:: Check Python
:: ============================================================
echo [检查环境]
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 3.9+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)
echo [OK] Python 已安装

:: ============================================================
:: Check dependencies
:: ============================================================
python -c "import playwright" >nul 2>&1
if errorlevel 1 (
    echo [提示] 检测到依赖未安装，正在自动安装...
    pip install -r "%SCRIPT_DIR%\requirements.txt"
    playwright install chromium
    if errorlevel 1 (
        echo [错误] 依赖安装失败，请检查网络连接
        pause
        exit /b 1
    )
    echo [OK] 依赖安装完成
) else (
    echo [OK] 依赖已就绪
)

:: ============================================================
:: Start Chrome remote debugging (if not already running)
:: ============================================================
echo.
echo [检查 Chrome 远程调试]
netstat -an | findstr ":%CDP_PORT%" >nul 2>&1
if errorlevel 1 (
    echo [提示] 正在启动 Chrome 远程调试模式...
    start "" "%CHROME_PATH%" --remote-debugging-port=%CDP_PORT% --user-data-dir="%USERPROFILE%\chrome-debug-profile"
    echo [等待] Chrome 启动中，请等待 5 秒...
    timeout /t 5 >nul
    echo [OK] Chrome 已启动
) else (
    echo [OK] Chrome 远程调试已在运行
)

:: ============================================================
:: Check image directory
:: ============================================================
echo.
if not exist "%IMAGE_DIR%" (
    echo [错误] 图片目录不存在: %IMAGE_DIR%
    echo [提示] 请确认路径正确并放入商品图片
    pause
    exit /b 1
)

:: ============================================================
:: Process all categories
:: ============================================================
echo.
echo ============================================================
echo   开始全自动上架...
echo ============================================================
echo.

set "TOTAL_CATEGORIES=0"
set "PROCESSED_CATEGORIES=0"

:: Process T-shirts (T恤 -> 3001)
if exist "%IMAGE_DIR%\T恤" (
    set /a TOTAL_CATEGORIES+=1
    echo [%date% %time%] ─────────────────────────────────
    echo [处理] 品类: T恤 ^| 代码: 3001
    echo [模式] 自动识别颜色
    echo [路径] %IMAGE_DIR%\T恤
    echo.
    python "%SCRIPT_DIR%\shein_auto_lister.py" --folder "%IMAGE_DIR%\T恤" --category 3001 --auto-color --base-product-id %BASE_PRODUCT_ID_TSHIRT%
    if not errorlevel 1 (
        set /a PROCESSED_CATEGORIES+=1
        echo [完成] T恤 上架完毕
    ) else (
        echo [警告] T恤 上架过程中出现错误
    )
    echo.
)

:: Process Hoodies (卫衣 -> 8008)
if exist "%IMAGE_DIR%\卫衣" (
    set /a TOTAL_CATEGORIES+=1
    echo [%date% %time%] ─────────────────────────────────
    echo [处理] 品类: 卫衣 ^| 代码: 8008
    echo [模式] 自动识别颜色
    echo [路径] %IMAGE_DIR%\卫衣
    echo.
    python "%SCRIPT_DIR%\shein_auto_lister.py" --folder "%IMAGE_DIR%\卫衣" --category 8008 --auto-color --base-product-id %BASE_PRODUCT_ID_HOODIE%
    if not errorlevel 1 (
        set /a PROCESSED_CATEGORIES+=1
        echo [完成] 卫衣 上架完毕
    ) else (
        echo [警告] 卫衣 上架过程中出现错误
    )
    echo.
)

:: Process Crewneck Sweatshirts (ady000 -> ady000)
if exist "%IMAGE_DIR%\ady000" (
    set /a TOTAL_CATEGORIES+=1
    echo [%date% %time%] ─────────────────────────────────
    echo [处理] 品类: 圆领卫衣 ^| 代码: ady000
    echo [模式] 自动识别颜色
    echo [路径] %IMAGE_DIR%\ady000
    echo.
    python "%SCRIPT_DIR%\shein_auto_lister.py" --folder "%IMAGE_DIR%\ady000" --category ady000 --auto-color --base-product-id %BASE_PRODUCT_ID_HOODIE%
    if not errorlevel 1 (
        set /a PROCESSED_CATEGORIES+=1
        echo [完成] 圆领卫衣 上架完毕
    ) else (
        echo [警告] 圆领卫衣 上架过程中出现错误
    )
    echo.
)

:: ============================================================
:: Summary
:: ============================================================
echo.
echo ============================================================
echo   全自动上架任务结束
echo ============================================================
echo.
echo   处理品类数: !TOTAL_CATEGORIES!
echo   成功品类数: !PROCESSED_CATEGORIES!
echo.

if !TOTAL_CATEGORIES! equ 0 (
    echo [警告] 未找到任何品类文件夹！
    echo [提示] 请确认以下目录中有商品图片:
    echo         %IMAGE_DIR%\T恤
    echo         %IMAGE_DIR%\卫衣
    echo         %IMAGE_DIR%\ady000
)

echo.
echo 按任意键退出...
pause >nul
exit /b 0
