# LapTest — Tracker

## In Progress
_nothing active_

## Backlog

### Features
- [ ] SMART raw attribute table (reallocated, pending, uncorrectable sectors) per-drive
- [ ] NVMe health via `smartctl` / WMI MSStorageDriver
- [ ] Per-core CPU frequency and temperature graph (live, 30s window)
- [ ] Battery discharge curve (log voltage + capacity over time while unplugged)
- [ ] Touchpad gesture test (tap, two-finger scroll, pinch detection)
- [ ] Screen uniformity test (gradient overlay to reveal backlight bleed)
- [ ] Color accuracy swatch panel (sRGB/DCI-P3 reference patches)
- [ ] USB port speed test (copy benchmark to/from plugged-in drive)
- [ ] Wi-Fi signal strength and channel graph
- [ ] Bluetooth device scan (list paired/nearby devices)
- [ ] Printer / docking-station port detection
- [ ] System summary PDF export (logo, scores, per-category tables)
- [ ] Print report button
- [ ] Saved sessions — compare two runs (before/after cleaning)
- [ ] Score weighting editor (user can mark which tests matter more)
- [ ] CLI mode: `python main.py --headless --output report.json`

### UI / UX
- [ ] System theme auto-detection (follow OS dark/light preference)
- [ ] Animated progress ring on the overall score tile
- [ ] Collapsible category cards on the dashboard
- [ ] Search/filter across all test results
- [ ] Tooltip with "what this means for buyers" for every test row
- [ ] Keyboard shortcut: `R` = Run all, `S` = Settings, `Esc` = back to dashboard
- [ ] Onboarding screen for first launch

### Localization
- [ ] German (de)
- [ ] Spanish (es)
- [ ] Turkish (tr)
- [ ] Chinese Simplified (zh-CN)

### Build / Packaging
- [ ] `app.ico` and `app.icns` icons
- [ ] GitHub Actions CI: build Windows artifact on push to `main`
- [ ] Inno Setup `.iss` script for a proper Windows installer (like DNgine)
- [ ] macOS DMG packaging step in `build_mac.sh`
- [ ] Auto-update check against GitHub releases

### Testing
- [ ] Unit tests for all formatter functions (`utils/formatters.py`)
- [ ] Unit tests for checker result shapes (mock WMI / psutil)
- [ ] Integration smoke test: import all modules, instantiate window, quit

## Done ✓
- [x] Project structure and all module scaffolding
- [x] 13 checker modules (storage, memory, cpu, gpu, display, battery, input, audio, webcam, network, ports, system, thermal)
- [x] Shared base widget system (`app/ui/base/widgets.py`)
- [x] Lazy translator with cache (en/ar/fr, RTL support)
- [x] Token-based theme engine (dark/light, hot-swap)
- [x] Settings persistence via QSettings
- [x] MultiWorker non-blocking test runner
- [x] Interactive keyboard test view
- [x] Dead pixel fullscreen test
- [x] Audio tone generator + mic record/playback (stdlib `wave`, no scipy)
- [x] Webcam live preview (OpenCV)
- [x] JSON export
- [x] PyInstaller spec + build scripts (Windows bat/ps1, macOS sh)
- [x] 64-bit venv (Python 3.14)
- [x] requirements.txt with all real deps (sounddevice, opencv-python, pyinstaller)
