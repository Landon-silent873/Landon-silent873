@echo off
chcp 65001 >nul 2>&1
title SHEIN 自动上架工具
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

:: ============================================================
:: Check Python
:: ============================================================
echo.
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
    timeout /t 3 >nul
    echo [OK] Chrome 已启动
) else (
    echo [OK] Chrome 远程调试已在运行
)

:: ============================================================
:: Menu
:: ============================================================
:menu
echo.
echo ============================================================
echo           SHEIN 自动上架工具 - 操作菜单
echo ============================================================
echo.
echo   1. 上架T恤（白色）
echo   2. 上架T恤（黑色）
echo   3. 上架卫衣（白色）
echo   4. 上架卫衣（黑色）
echo   5. 上架圆领卫衣（白色）
echo   6. 上架圆领卫衣（黑色）
echo   7. 自动识别颜色模式（根据文件夹名判断）
echo   0. 退出
echo.
echo ============================================================
echo.
set /p choice="请输入选项编号: "

if "%choice%"=="1" goto tshirt_white
if "%choice%"=="2" goto tshirt_black
if "%choice%"=="3" goto hoodie_white
if "%choice%"=="4" goto hoodie_black
if "%choice%"=="5" goto crewneck_white
if "%choice%"=="6" goto crewneck_black
if "%choice%"=="7" goto auto_color
if "%choice%"=="0" goto end

echo [错误] 无效选项，请重新输入
goto menu

:: ============================================================
:: Launch commands
:: ============================================================
:tshirt_white
echo.
echo [启动] 上架T恤（白色）...
python "%SCRIPT_DIR%\shein_auto_lister.py" --folder "%IMAGE_DIR%\T恤" --category 3001 --color W --base-product-id %BASE_PRODUCT_ID_TSHIRT%
goto done

:tshirt_black
echo.
echo [启动] 上架T恤（黑色）...
python "%SCRIPT_DIR%\shein_auto_lister.py" --folder "%IMAGE_DIR%\T恤" --category 3001 --color B --base-product-id %BASE_PRODUCT_ID_TSHIRT%
goto done

:hoodie_white
echo.
echo [启动] 上架卫衣（白色）...
python "%SCRIPT_DIR%\shein_auto_lister.py" --folder "%IMAGE_DIR%\卫衣" --category 8008 --color W --base-product-id %BASE_PRODUCT_ID_HOODIE%
goto done

:hoodie_black
echo.
echo [启动] 上架卫衣（黑色）...
python "%SCRIPT_DIR%\shein_auto_lister.py" --folder "%IMAGE_DIR%\卫衣" --category 8008 --color B --base-product-id %BASE_PRODUCT_ID_HOODIE%
goto done

:crewneck_white
echo.
echo [启动] 上架圆领卫衣（白色）...
python "%SCRIPT_DIR%\shein_auto_lister.py" --folder "%IMAGE_DIR%\ady000" --category ady000 --color W --base-product-id %BASE_PRODUCT_ID_HOODIE%
goto done

:crewneck_black
echo.
echo [启动] 上架圆领卫衣（黑色）...
python "%SCRIPT_DIR%\shein_auto_lister.py" --folder "%IMAGE_DIR%\ady000" --category ady000 --color B --base-product-id %BASE_PRODUCT_ID_HOODIE%
goto done

:auto_color
echo.
echo [启动] 自动识别颜色模式...
echo.

:: Process T-shirts
if exist "%IMAGE_DIR%\T恤" (
    echo [处理] T恤 - 品类代码 3001
    python "%SCRIPT_DIR%\shein_auto_lister.py" --folder "%IMAGE_DIR%\T恤" --category 3001 --auto-color --base-product-id %BASE_PRODUCT_ID_TSHIRT%
    echo.
)

:: Process Hoodies
if exist "%IMAGE_DIR%\卫衣" (
    echo [处理] 卫衣 - 品类代码 8008
    python "%SCRIPT_DIR%\shein_auto_lister.py" --folder "%IMAGE_DIR%\卫衣" --category 8008 --auto-color --base-product-id %BASE_PRODUCT_ID_HOODIE%
    echo.
)

:: Process Crewneck Sweatshirts
if exist "%IMAGE_DIR%\ady000" (
    echo [处理] 圆领卫衣 - 品类代码 ady000
    python "%SCRIPT_DIR%\shein_auto_lister.py" --folder "%IMAGE_DIR%\ady000" --category ady000 --auto-color --base-product-id %BASE_PRODUCT_ID_HOODIE%
    echo.
)
goto done

:: ============================================================
:: End
:: ============================================================
:done
echo.
echo ============================================================
echo   任务执行完毕！
echo ============================================================
echo.
pause
exit /b 0

:end
echo.
echo 已退出。
exit /b 0
