@echo off
echo ============================================
echo   SHEIN Auto-Lister - Install Dependencies
echo ============================================
echo.
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found!
    echo Please install Python 3.9+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH"
    pause
    exit /b 1
)
echo [OK] Python found
echo.
echo Installing dependencies...
pip install -r "%~dp0requirements.txt"
if errorlevel 1 (
    echo [ERROR] pip install failed. Check your network.
    pause
    exit /b 1
)
echo.
echo Installing Playwright browser...
playwright install chromium
if errorlevel 1 (
    echo [ERROR] Playwright install failed. Check your network.
    pause
    exit /b 1
)
echo.
echo ============================================
echo   Installation complete!
echo   Now double-click "start.bat" to begin.
echo ============================================
pause
