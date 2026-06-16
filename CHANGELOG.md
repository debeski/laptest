# Changelog

All notable changes to LapTest will be documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [0.2.1] — 2026-06-01

### Added

- **CI/CD pipeline**: GitHub Actions builds and packages on Windows (PyInstaller onedir + Inno Setup installer) and macOS (`.app` bundle). Tag-driven (`v*`) releases attach `LapTest-Setup-<ver>.exe` and `LapTest-<ver>-macos.zip` to a GitHub Release, with notes pulled from this changelog.

### Changed

- **macOS bundle version**: `CFBundleShortVersionString`/`CFBundleVersion` in `laptest.spec` now read from the `VERSION` file instead of a hardcoded `0.2.0`.

### Fixed — macOS polish

- **Keyboard test layout**: Mac now shows the correct keyboard map — `Cmd`/`Option`/`Ctrl` bottom row, `Delete`/`Return` labels, and arrow keys (`←` `→` `↑` `↓`). Key events map correctly: `Key_Meta → Cmd`, `Key_Alt → Option`, `Key_Backspace → Delete`. Duplicate keys (two Shift, two Cmd, two Option) tracked independently.
- **Audio tones**: speaker test now uses `sounddevice` directly (cross-platform, no subprocess). Falls back to `afplay` on macOS / `aplay` on Linux / `winsound` on Windows. Previously fell through to `aplay` on macOS (Linux-only tool), producing silence.
- **Audio mic recording**: added error display if `sounddevice` raises (e.g., permission denied). Added macOS privacy hint pointing to System Settings → Privacy & Security → Microphone.
- **Audio checker**: added macOS backend via `system_profiler SPAudioDataType`. Now detects built-in speakers and microphone by name (e.g., "MacBook Pro Speakers", "MacBook Pro Microphone"). Falls back to `sounddevice.query_devices()` if profiler returns nothing.
- **Battery health** (Apple Silicon): `MaxCapacity` in ioreg returns `100` on M-series (a percentage scale, not mAh). Now reads `AppleRawMaxCapacity` first; falls back to `MaxCapacity` only when it looks like actual mAh (> 100). Prevents the "1.6% healthy" bug.
- **Wi-Fi display**: card-type string from `SPAirPortDataType` included raw hex vendor IDs like `(0x14E4, 0x4387)`. Now stripped with regex. Connected value shows `Connected — "SSID"` or `<adapter> (not connected)`.
- **Settings icon too small**: `QPushButton[app-btn="icon"]` now sets `font-size: 18px` explicitly so the ⚙ emoji renders at a readable size on macOS (previously inherited 13 px body font).
- **Webcam checker**: added `system_profiler SPCameraDataType` macOS detection so the checker shows camera name (e.g., "FaceTime HD Camera (Built-in)") even without OpenCV installed.
- **Webcam test dialog**: improved error messages — "opencv-python not installed — run: pip install opencv-python" and macOS-specific camera permission guidance.
- **laptest.spec**: added `NSMicrophoneUsageDescription` + `NSCameraUsageDescription` to macOS `Info.plist` — without these keys the OS silently blocks mic/camera access even after the user grants permission in System Settings.

---

## [0.2.0] — 2026-06-01

### Added — macOS native backends

All checkers now have a proper macOS code path alongside the existing Windows (WMI) path. The two are fully separated; no macOS-only code is reached on Windows and vice versa.

| Category | macOS source |
|---|---|
| **GPU** | `system_profiler SPDisplaysDataType` — model, vendor, GPU cores, VRAM (or "Shared" for Apple Silicon) |
| **Network** | `system_profiler SPAirPortDataType` + `SPNetworkDataType` + `SPBluetoothDataType` — Wi-Fi name, connected SSID, standard (802.11ac/ax…), Ethernet, Bluetooth |
| **Ports** | `system_profiler SPUSBDataType` + `SPThunderboltDataType` + `SPCardReaderDataType` + `SPAudioDataType` — Thunderbolt version/count, USB 3.x controllers, USB-C, SD card reader, 3.5 mm jack |
| **System / BIOS** | `system_profiler SPHardwareDataType` (machine model, chip, firmware); `ioreg AppleLMUController` (ALS); `csrutil`/`SPiBridgeDataType` (Secure Boot); Secure Enclave / T2 chip in place of TPM |
| **Storage** | `system_profiler SPStorageDataType` — deduplicated physical drive list with model, type (NVMe/SSD), capacity, SMART "Verified" status; APFS/GPT noted as default |
| **Memory** | `system_profiler SPMemoryDataType` — type (LPDDR5/DDR4), speed, per-DIMM detail for Intel; "Unified (soldered)" for Apple Silicon |
| **Battery** | `ioreg AppleSmartBattery` — health %, wear, capacity (mAh), cycle count, temperature, voltage; Apple-adjusted cycle thresholds (500/1000 vs 300/600 on Windows) |
| **Input Devices** | `ioreg AppleMultitouchTrackpad` for trackpad; `sysctl hw.model` for keyboard; `SPiBridgeDataType` / `arm64` detection for Touch ID |
| **CPU** | `sysctl machdep.cpu.brand_string` (Intel) / `system_profiler SPHardwareDataType` (Apple Silicon) for model name |
| **Thermal** | `psutil.sensors_temperatures()` on Intel; informational note + `sudo powermetrics` guidance on Apple Silicon |

### Changed
- `laptest.spec`: Windows-only hidden imports (`wmi`, `win32api`, etc.) now wrapped in `if sys.platform == "win32"` — macOS builds no longer warn about missing packages
- `requirements.txt`: removed `py-cpuinfo` (unused since 0.1.1; was root cause of false second-instance popups)
- `laptest.spec`: removed `collect_submodules("cpuinfo")` entry
- `laptest.spec`: updated `CFBundleShortVersionString` to `0.2.0`

---

## [0.1.1] — 2026-06-01

### Fixed
- **CMD windows + false second-instance popup**: root cause was `py-cpuinfo` spawning a new Python subprocess internally — replaced with direct WMI (`Win32_Processor`) for all CPU data, eliminating the subprocess entirely. All other `subprocess.run` calls now pass `CREATE_NO_WINDOW` + `STARTF_USESHOWWINDOW` via the central `run_command()`/`run_ps()` helpers
- **Result text misalignment**: switched result rows from individual `QHBoxLayout` widgets to a single shared `QGridLayout` per card with a fixed 175 px label column — guarantees pixel-perfect column alignment across all rows
- **Sidebar removed**: navigation sidebar replaced by a gear icon `⚙` in the main toolbar; settings page gains a `← Back` button; no visual/interaction regression
- **Font size spinner**: `QSpinBox` up/down buttons were obscured by incorrect padding from the shared QLineEdit style; now has its own full QSS block with explicit `subcontrol-position` for both arrow buttons; also constrained to a fixed width so buttons are always reachable
- **Inno Setup script added**: `laptest.iss` reads version from `VERSION` file, bundles `dist\LapTest\*`, supports EN/AR/FR installer language, uses the same `AppMutex` as the runtime single-instance guard

### Changed
- `cpu.py` no longer depends on `py-cpuinfo` (can be removed from `requirements.txt` if desired — WMI gives equivalent or better data on Windows)
- Settings view now emits `back_requested` signal; main window handles it by switching the stack back to dashboard
- Score tiles use `h2` heading instead of `h1` for better visual balance without sidebar

---

## [0.1.0] — 2026-06-01

### Added
- Initial release
- 13 hardware test categories: Storage, Memory, CPU, GPU, Display, Battery, Input Devices, Audio, Camera, Network, Ports & Slots, System & BIOS, Thermals & Fans
- Interactive keyboard key-press test (visual keyboard map)
- Dead pixel fullscreen color test (8 colors, click to cycle)
- Speaker tone generator (440 Hz, 1 kHz, 300 Hz, 2 kHz)
- Microphone record & playback test (3-second capture, stdlib WAV)
- Webcam live preview via OpenCV
- Real-time language switching: English, Arabic (RTL), French
- Dark and Light themes with token-based QSS hot-swap
- Accessibility settings: high contrast, large text, reduce motion
- All UI built from shared base widget classes
- Non-blocking test runner via QThread MultiWorker
- Per-card individual `▶` run button
- Interactive test dialogs (`QDialog`) launched from category cards
- JSON export of full diagnostic report
- PyInstaller onedir build scripts: `build_windows.bat`, `build_windows.ps1`, `build_mac.sh`
- `QSharedMemory` single-instance guard
