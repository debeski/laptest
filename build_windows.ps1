# LapTest Windows Build Script (PowerShell)
$ErrorActionPreference = "Stop"

$ROOT_DIR  = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ROOT_DIR

$VENV_PATH = Join-Path $ROOT_DIR "venv"

# Resolve Python — prefer py launcher pointing to 64-bit, fall back to plain python
function Get-Python64 {
    # Try py launcher entries from newest to oldest
    foreach ($ver in @("3.14", "3.13", "3.12", "3.11", "3.10", "3")) {
        try {
            $bits = & py "-$ver" -c "import sys; print(sys.maxsize > 2**32)" 2>$null
            if ($bits -eq "True") { return "py -$ver" }
        } catch {}
    }
    # Try plain python
    try {
        $bits = & python -c "import sys; print(sys.maxsize > 2**32)" 2>$null
        if ($bits -eq "True") { return "python" }
    } catch {}
    return $null
}

$PYTHON_CMD = Get-Python64
if (-not $PYTHON_CMD) {
    Write-Host "ERROR: No 64-bit Python found. Install Python 3.11+ (64-bit) from https://python.org" -ForegroundColor Red
    exit 1
}

Write-Host "Using Python: $PYTHON_CMD" -ForegroundColor Cyan

if (-not (Test-Path $VENV_PATH)) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    Invoke-Expression "$PYTHON_CMD -m venv `"$VENV_PATH`""
}

Write-Host "Activating virtual environment..." -ForegroundColor Green
. (Join-Path $VENV_PATH "Scripts\Activate.ps1")

Write-Host "Installing / updating build dependencies..." -ForegroundColor Cyan
python -m pip install --upgrade pip --quiet
python -m pip install -r requirements.txt pyinstaller --quiet

Write-Host "Cleaning previous build artifacts..." -ForegroundColor Magenta
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist")  { Remove-Item -Recurse -Force "dist"  }

Write-Host "Building Windows onedir package..." -ForegroundColor Green
python -m PyInstaller --noconfirm --clean laptest.spec

if ($LASTEXITCODE -ne 0) {
    Write-Host "Build failed." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Build complete:  dist\LapTest\" -ForegroundColor Yellow
Write-Host "Launcher:        dist\LapTest\LapTest.exe" -ForegroundColor Green
