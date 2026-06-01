# LapTest

A desktop diagnostic tool for evaluating second-hand laptops before purchase.
Built with PyQt6. Runs on Windows and macOS.

## Features

- **13 hardware test categories** — Storage (SMART, speed, MBR/GPT), RAM (type, speed, dual-channel), CPU (model, generation, temp, throttling), GPU (VRAM, driver), Display (resolution, PPI, refresh rate), Battery (health, wear, cycles), Input Devices (keyboard, touchpad, fingerprint), Audio (speakers, mic), Camera (live preview), Network (Wi-Fi standard, Bluetooth), Ports & Slots (USB 2/3/C, Thunderbolt, SD), System / BIOS (boot mode, Secure Boot, TPM / Secure Enclave, activation), Thermals & Fans
- **Interactive tests** — keyboard key-map test, dead-pixel fullscreen color test, speaker tone generator, microphone record & playback, webcam live preview
- **Multilingual** — English, Arabic (RTL), French — live switching, no restart needed
- **Dark / Light themes** — hot-swapped at runtime
- **Accessibility** — high contrast, large text, reduce motion
- **JSON report export**

## Platform Coverage

| Feature | Windows | macOS |
|---|---|---|
| CPU model / speed / usage | WMI + psutil | `sysctl` / `system_profiler` + psutil |
| GPU model / VRAM | WMI + registry | `system_profiler SPDisplaysDataType` |
| RAM type / speed / slots | WMI | `system_profiler SPMemoryDataType` |
| Storage SMART / type | PowerShell `Get-PhysicalDisk` | `system_profiler SPStorageDataType` |
| Battery health / cycles | WMI + `root/wmi` | `ioreg AppleSmartBattery` |
| Network (Wi-Fi / BT) | WMI | `system_profiler SPAirPort/Network/Bluetooth` |
| Ports (USB / Thunderbolt) | PnP `Get-PnpDevice` | `system_profiler SPUSB/Thunderbolt` |
| Fingerprint / Touch ID | WMI PnP scan | `SPiBridgeDataType` / arm64 detection |
| BIOS / Firmware | WMI + registry | `system_profiler SPHardwareDataType` |
| Secure Boot / TPM | `Get-Tpm` + registry | Secure Enclave / T2 via `SPiBridgeDataType` |
| Temperature sensors | WMI `MSAcpi_ThermalZoneTemperature` | `psutil` (Intel); note for Apple Silicon† |
| Display / Battery / Keyboard | psutil + Qt | psutil + Qt |

†Apple Silicon restricts SMC sensor access; run `sudo powermetrics --samplers smc` in Terminal for live temperatures.

## Requirements

- Python 3.11+ **64-bit** (PyQt6 wheels are 64-bit only)
- Windows 10/11 or macOS 12+

## Quick Start

```bash
# Clone / download the project, then:
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # macOS

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

> The `.app` bundle is the correct native macOS format. Distribute the entire `LapTest.app` folder or wrap it in a DMG.

## Project Structure

```
Laptest/
├── main.py                  Entry point
├── laptest.spec             PyInstaller spec (platform-aware)
├── app/
│   ├── core/                Settings, translator, theme engine
│   ├── checkers/            One module per hardware category
│   │                        Each checker has Windows (WMI) and macOS
│   │                        (system_profiler / ioreg) branches
│   ├── ui/
│   │   ├── base/widgets.py  All shared base widget classes
│   │   ├── components/      Result cards
│   │   └── views/           Dashboard, settings, interactive tests
│   └── utils/               Formatters, platform helpers, QThread workers
├── locales/                 en / ar / fr JSON translation files
└── assets/themes/           dark.json / light.json token files
```

## Version

See [VERSION](VERSION) and [CHANGELOG](CHANGELOG.md).
