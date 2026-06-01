# LapTest

A desktop diagnostic tool for evaluating second-hand laptops before purchase.
Built with PyQt6. Runs on Windows and macOS.

## Features

- **13 hardware test categories** — Storage (SMART, speed, MBR/GPT), RAM (type, speed, dual-channel), CPU (model, generation, temp, throttling), GPU (VRAM, driver), Display (resolution, PPI, refresh rate), Battery (health, wear, cycles), Input Devices (keyboard, touchpad, fingerprint), Audio (speakers, mic), Camera (live preview), Network (Wi-Fi standard, Bluetooth), Ports & Slots (USB 2/3/C, HDMI, SD), System & BIOS (boot mode, Secure Boot, TPM, activation), Thermals & Fans
- **Interactive tests** — keyboard key-map test, dead-pixel fullscreen color test, speaker tone generator, microphone record & playback, webcam live preview
- **Multilingual** — English, Arabic (RTL), French — live switching, no restart needed
- **Dark / Light themes** — hot-swapped at runtime
- **Accessibility** — high contrast, large text, reduce motion
- **JSON report export**

## Requirements

- Python 3.11+ **64-bit** (PyQt6 wheels are 64-bit only)
- Windows 10/11 or macOS 12+

## Quick Start

```bash
# Clone / download the project, then:
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # macOS / Linux

pip install -r requirements.txt
python main.py
```

Or just double-click **`run.bat`** on Windows.

## Build Standalone Package

**Windows**
```bat
build_windows.bat
# or
.\build_windows.ps1
```
Output: `dist\LapTest\LapTest.exe`

**macOS**
```bash
chmod +x build_mac.sh
./build_mac.sh
```
Output: `dist/LapTest.app`

## Project Structure

```
Laptest/
├── main.py                  Entry point
├── laptest.spec             PyInstaller spec
├── app/
│   ├── core/                Settings, translator, theme engine
│   ├── checkers/            One module per hardware category
│   ├── ui/
│   │   ├── base/widgets.py  All shared base widget classes
│   │   ├── components/      Sidebar, result cards
│   │   └── views/           Dashboard, settings, interactive tests
│   └── utils/               Formatters, platform helpers, QThread workers
├── locales/                 en / ar / fr JSON translation files
└── assets/themes/           dark.json / light.json token files
```

## Version

See [VERSION](VERSION) and [CHANGELOG](CHANGELOG.md).
