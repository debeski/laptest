# Changelog

All notable changes to LapTest will be documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
