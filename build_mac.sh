#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "build_mac.sh must be run on macOS."
    exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 is required. Install via: brew install python"
    exit 1
fi

# Verify 64-bit (arm64 or x86_64 — both fine for PyQt6)
ARCH="$(python3 -c 'import platform; print(platform.machine())')"
echo "Python arch: $ARCH"

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

echo "Installing / updating build dependencies..."
python -m pip install --upgrade pip --quiet
python -m pip install -r requirements.txt pyinstaller --quiet

echo "Cleaning previous build artifacts..."
rm -rf build dist

echo "Building macOS app bundle..."
python -m PyInstaller --noconfirm --clean laptest.spec

deactivate

echo ""
echo "Build complete:  dist/LapTest.app"
echo "Launcher:        dist/LapTest.app/Contents/MacOS/LapTest"
