@echo off
setlocal enabledelayedexpansion

set "ROOT_DIR=%~dp0"
pushd "%ROOT_DIR%"

:: Prefer py launcher with 64-bit Python 3, fall back to plain python
where py >nul 2>nul
if %errorlevel%==0 (
    set "PYTHON_CMD=py -3"
) else (
    set "PYTHON_CMD=python"
)

:: Verify 64-bit (PyQt6 wheels are 64-bit only)
%PYTHON_CMD% -c "import sys; exit(0 if sys.maxsize > 2**32 else 1)"
if errorlevel 1 (
    echo ERROR: 64-bit Python is required. The current Python is 32-bit.
    echo        Install Python 3.11+ 64-bit from https://python.org
    popd
    exit /b 1
)

if not exist "venv" (
    echo Creating virtual environment...
    %PYTHON_CMD% -m venv venv
)

call "venv\Scripts\activate.bat"
if errorlevel 1 (
    echo Failed to activate the virtual environment.
    popd
    exit /b 1
)

echo Installing / updating build dependencies...
python -m pip install --upgrade pip --quiet
python -m pip install -r requirements.txt pyinstaller --quiet

echo Cleaning previous build artifacts...
if exist build   rmdir /s /q build
if exist dist    rmdir /s /q dist

echo Building Windows onedir package...
python -m PyInstaller --noconfirm --clean laptest.spec
if errorlevel 1 (
    echo Build failed.
    popd
    exit /b 1
)

echo.
echo Build complete:  dist\LapTest\
echo Launcher:        dist\LapTest\LapTest.exe
popd
endlocal
