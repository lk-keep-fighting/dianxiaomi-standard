@echo off
rem Digital Chief Automation Project - Dependency Installation Script (Windows)
rem This script installs all required dependencies for the browser automation project

setlocal enabledelayedexpansion

echo ==================================================
echo   Digital Chief Automation - Dependency Installer
echo ==================================================

:check_python
echo 🔍 Checking Python installation...

rem Check if python command exists
python --version >nul 2>&1
if !errorlevel! equ 0 (
    set PYTHON_CMD=python
    goto check_python_version
)

rem Check if python3 command exists
python3 --version >nul 2>&1
if !errorlevel! equ 0 (
    set PYTHON_CMD=python3
    goto check_python_version
)

echo ❌ Error: Python is not installed or not in PATH
echo Please install Python 3.7+ from https://www.python.org/
pause
exit /b 1

:check_python_version
for /f "tokens=2" %%i in ('%PYTHON_CMD% --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✅ Found Python: %PYTHON_VERSION%

rem Simple version check - just ensure it starts with 3.
echo %PYTHON_VERSION% | findstr /r "^3\.[789]" >nul
if !errorlevel! neq 0 (
    echo %PYTHON_VERSION% | findstr /r "^3\.1[0-9]" >nul
    if !errorlevel! neq 0 (
        echo ❌ Error: Python 3.7+ is required, found %PYTHON_VERSION%
        pause
        exit /b 1
    )
)

:check_pip
echo 🔍 Checking pip installation...

rem Check if pip command exists
pip --version >nul 2>&1
if !errorlevel! equ 0 (
    set PIP_CMD=pip
    goto pip_found
)

rem Check if pip3 command exists
pip3 --version >nul 2>&1
if !errorlevel! equ 0 (
    set PIP_CMD=pip3
    goto pip_found
)

echo ❌ Error: pip is not installed
echo Please install pip or use '%PYTHON_CMD% -m pip' instead
pause
exit /b 1

:pip_found
for /f "tokens=*" %%i in ('%PIP_CMD% --version 2^>^&1') do set PIP_VERSION=%%i
echo ✅ Found pip: %PIP_VERSION%

:create_venv
if "%1"=="--venv" (
    echo.
    echo 🐍 Creating virtual environment...
    
    if not exist "venv" (
        %PYTHON_CMD% -m venv venv
        echo ✅ Virtual environment created
    ) else (
        echo ℹ️  Virtual environment already exists
    )
    
    echo 📝 To activate virtual environment, run:
    echo    venv\Scripts\activate     (Windows)
    echo    source venv/bin/activate  (Linux/macOS)
    echo.
    
    set /p ACTIVATE_VENV="Do you want to activate the virtual environment now? (y/n): "
    if /i "!ACTIVATE_VENV!"=="y" (
        call venv\Scripts\activate
        echo ✅ Virtual environment activated
    )
)

:install_python_deps
echo.
echo 📦 Installing Python dependencies...

rem Upgrade pip first
echo ⬆️  Upgrading pip...
%PIP_CMD% install --upgrade pip
if !errorlevel! neq 0 (
    echo ❌ Failed to upgrade pip
    pause
    exit /b 1
)

rem Install dependencies from requirements.txt
echo 📋 Installing from requirements.txt...
%PIP_CMD% install -r requirements.txt
if !errorlevel! neq 0 (
    echo ❌ Failed to install Python dependencies
    pause
    exit /b 1
)

echo ✅ Python dependencies installed successfully

:install_playwright_browsers
echo.
echo 🌐 Installing Playwright browsers...

rem Install browser binaries
%PYTHON_CMD% -m playwright install
if !errorlevel! neq 0 (
    echo ❌ Failed to install Playwright browsers
    pause
    exit /b 1
)

echo ✅ Playwright browsers installed successfully

:verify_installation
echo.
echo 🔍 Verifying installation...

rem Check if playwright is properly installed
%PYTHON_CMD% -c "import playwright; print('Playwright version:', playwright.__version__)" >nul 2>&1
if !errorlevel! equ 0 (
    echo ✅ Playwright is working correctly
) else (
    echo ❌ Playwright installation verification failed
    pause
    exit /b 1
)

rem Check if pytest is working
%PYTHON_CMD% -c "import pytest; print('Pytest version:', pytest.__version__)" >nul 2>&1
if !errorlevel! equ 0 (
    echo ✅ Pytest is working correctly
) else (
    echo ❌ Pytest installation verification failed
    pause
    exit /b 1
)

echo ✅ All dependencies verified successfully

:show_usage
echo.
echo 🚀 Installation completed successfully!
echo.
echo Next steps:
echo 1. Run the main application:
echo    run.bat               (Windows)
echo    ./run.sh              (Linux/macOS)
echo    python src/main_refactored_dianxiaomi.py    (Direct)
echo.
echo 2. Run tests (archived utilities):
echo    pytest archive/non_startup_assets/tests/
echo.
echo 3. For development with virtual environment:
echo    install_dependencies.bat --venv
echo.

pause
exit /b 0