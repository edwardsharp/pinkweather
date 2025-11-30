@echo off
REM PinkWeather Installation Script for Windows
REM This script sets up the development environment for the weather display system

setlocal enabledelayedexpansion

REM Colors for output (using Windows color codes)
set "RED=[91m"
set "GREEN=[92m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "NC=[0m"

REM Function-like labels for colored output
goto :main

:print_status
echo %BLUE%[INFO]%NC% %~1
goto :eof

:print_success
echo %GREEN%[SUCCESS]%NC% %~1
goto :eof

:print_warning
echo %YELLOW%[WARNING]%NC% %~1
goto :eof

:print_error
echo %RED%[ERROR]%NC% %~1
goto :eof

:command_exists
where %1 >nul 2>&1
goto :eof

:detect_python
REM Check for python3 first, then python
where python3 >nul 2>&1
if !errorlevel! equ 0 (
    python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" >nul 2>&1
    if !errorlevel! equ 0 (
        set "PYTHON_CMD=python3"
        goto :eof
    )
)

where python >nul 2>&1
if !errorlevel! equ 0 (
    python -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" >nul 2>&1
    if !errorlevel! equ 0 (
        set "PYTHON_CMD=python"
        goto :eof
    )
)

set "PYTHON_CMD="
goto :eof

:detect_pip
REM Check for pip3 first, then pip
where pip3 >nul 2>&1
if !errorlevel! equ 0 (
    set "PIP_CMD=pip3"
    goto :eof
)

where pip >nul 2>&1
if !errorlevel! equ 0 (
    set "PIP_CMD=pip"
    goto :eof
)

REM Try using python -m pip
if not "%PYTHON_CMD%"=="" (
    %PYTHON_CMD% -m pip --version >nul 2>&1
    if !errorlevel! equ 0 (
        set "PIP_CMD=%PYTHON_CMD% -m pip"
        goto :eof
    )
)

set "PIP_CMD="
goto :eof

:main
echo ==================================================
echo PinkWeather Installation Script
echo Weather Display System Setup - Windows
echo ==================================================
echo.

REM Check if we're in the right directory
if not exist "display_renderer.py" (
    call :print_error "Please run this script from the pinkweather directory"
    call :print_error "Required files not found: display_renderer.py, http_server.py"
    pause
    exit /b 1
)

if not exist "http_server.py" (
    call :print_error "Please run this script from the pinkweather directory"
    call :print_error "Required files not found: display_renderer.py, http_server.py"
    pause
    exit /b 1
)

call :print_status "Checking system requirements..."

REM Detect Python
call :detect_python
if "%PYTHON_CMD%"=="" (
    call :print_error "Python 3.8+ not found"
    call :print_error "Please install Python 3.8 or later:"
    echo   • Download from: https://python.org/downloads/
    echo   • Make sure to check 'Add Python to PATH' during installation
    echo   • After installation, restart Command Prompt and try again
    pause
    exit /b 1
)

REM Check Python version
for /f "tokens=*" %%i in ('%PYTHON_CMD% -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"') do set PYTHON_VERSION=%%i
call :print_success "Found Python %PYTHON_VERSION% (%PYTHON_CMD%)"

REM Detect pip
call :detect_pip
if "%PIP_CMD%"=="" (
    call :print_error "pip not found"
    call :print_error "Please ensure pip is installed with Python"
    call :print_error "Try reinstalling Python with pip included"
    pause
    exit /b 1
)

call :print_success "Found pip (%PIP_CMD%)"

REM Ask user about installation type
echo.
echo Installation options:
echo 1) Development setup with virtual environment (recommended)
echo 2) System-wide installation
echo 3) Just check dependencies
echo.
set /p choice="Choose option [1-3]: "

if "%choice%"=="1" goto :install_with_venv
if "%choice%"=="2" goto :install_system_wide
if "%choice%"=="3" goto :check_dependencies_only

call :print_error "Invalid choice. Exiting."
pause
exit /b 1

:install_with_venv
call :print_status "Setting up virtual environment..."

REM Create virtual environment
if exist "venv" (
    call :print_warning "Virtual environment already exists"
    set /p recreate="Remove existing venv and recreate? [y/N]: "
    if /i "!recreate!"=="y" (
        rmdir /s /q venv
        %PYTHON_CMD% -m venv venv
    )
) else (
    %PYTHON_CMD% -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

call :print_success "Virtual environment created and activated"

REM Upgrade pip
call :print_status "Upgrading pip..."
python -m pip install --upgrade pip

REM Install dependencies
call :print_status "Installing dependencies..."
pip install -r requirements.txt

REM Run verification
call :print_status "Running installation verification..."
python check_install.py

call :print_success "Installation complete!"
echo.
echo To use the development environment:
echo   1. Activate virtual environment: venv\Scripts\activate.bat
echo   2. Start development server: python http_server.py
echo   3. Open http://localhost:8000 in your browser
echo.
echo To deactivate virtual environment later: deactivate
echo.
pause
goto :eof

:install_system_wide
call :print_warning "Installing system-wide..."
call :print_warning "This may affect other Python projects"

set /p confirm="Continue with system-wide installation? [y/N]: "
if /i not "!confirm!"=="y" (
    call :print_status "Installation cancelled"
    pause
    exit /b 0
)

REM Try to install dependencies
call :print_status "Installing dependencies..."

REM First try normal installation
%PIP_CMD% install -r requirements.txt >nul 2>&1
if !errorlevel! equ 0 goto :system_install_success

REM If that fails, try with --user flag
call :print_warning "Trying --user installation"
%PIP_CMD% install --user -r requirements.txt >nul 2>&1
if !errorlevel! equ 0 goto :system_install_success

call :print_error "Cannot install packages. Try creating a virtual environment instead."
call :print_error "Run this script again and choose option 1"
pause
exit /b 1

:system_install_success
REM Run verification
call :print_status "Running installation verification..."
%PYTHON_CMD% check_install.py

call :print_success "System-wide installation complete!"
echo.
echo To start development server: %PYTHON_CMD% http_server.py
echo To generate previews: %PYTHON_CMD% weather_example.py
echo.
pause
goto :eof

:check_dependencies_only
call :print_status "Checking dependencies without installing..."

if exist "venv\Scripts\activate.bat" (
    call :print_status "Found virtual environment, checking within venv..."
    call venv\Scripts\activate.bat
    python check_install.py
) else (
    %PYTHON_CMD% check_install.py
)
pause
goto :eof

REM Handle command line arguments
if "%1"=="--help" goto :show_help
if "%1"=="-h" goto :show_help
if "%1"=="--venv" goto :cmd_venv
if "%1"=="--system" goto :cmd_system
if "%1"=="--check" goto :cmd_check
if "%1"=="" goto :main

call :print_error "Unknown option: %1"
call :print_error "Use --help for usage information"
pause
exit /b 1

:show_help
echo Usage: %0 [option]
echo.
echo Options:
echo   --help, -h     Show this help message
echo   --venv         Install with virtual environment
echo   --system       Install system-wide
echo   --check        Check dependencies only
echo.
echo If no option provided, interactive mode will be used.
pause
exit /b 0

:cmd_venv
call :detect_python
call :detect_pip
if "%PYTHON_CMD%"=="" (
    call :print_error "Python 3.8+ is required"
    pause
    exit /b 1
)
if "%PIP_CMD%"=="" (
    call :print_error "pip is required"
    pause
    exit /b 1
)
goto :install_with_venv

:cmd_system
call :detect_python
call :detect_pip
if "%PYTHON_CMD%"=="" (
    call :print_error "Python 3.8+ is required"
    pause
    exit /b 1
)
if "%PIP_CMD%"=="" (
    call :print_error "pip is required"
    pause
    exit /b 1
)
goto :install_system_wide

:cmd_check
call :detect_python
if "%PYTHON_CMD%"=="" (
    call :print_error "Python 3.8+ is required"
    pause
    exit /b 1
)
goto :check_dependencies_only
