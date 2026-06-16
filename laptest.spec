# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

project_root = Path(SPECPATH)
_version_file = project_root / "VERSION"
app_version = _version_file.read_text(encoding="utf-8").strip() if _version_file.exists() else "0.0.0"


def collect_tree(relative_root: str):
    root = project_root / relative_root
    items = []
    for path in root.rglob("*"):
        if path.is_file() and "__pycache__" not in path.parts:
            dest = str(path.parent.relative_to(project_root))
            items.append((str(path), dest))
    return items


# ── Data files ────────────────────────────────────────────────────────────
datas = []
datas += collect_tree("locales")
datas += collect_tree("assets")
datas += collect_data_files("sounddevice", include_py_files=False)
datas += collect_data_files("cv2")

# ── Hidden imports ────────────────────────────────────────────────────────
hiddenimports = []
hiddenimports += collect_submodules("app.checkers")
hiddenimports += collect_submodules("app.core")
hiddenimports += collect_submodules("app.ui")
hiddenimports += collect_submodules("app.utils")
hiddenimports += collect_submodules("psutil")
hiddenimports += collect_submodules("sounddevice")
hiddenimports += collect_submodules("cv2")
hiddenimports += ["numpy", "numpy.core", "numpy.core._multiarray_umath"]

# Windows-only deps — do not add on macOS (packages not installed there)
if sys.platform == "win32":
    hiddenimports += ["wmi", "win32api", "win32con", "win32security",
                       "pywintypes", "pythoncom"]

# ── Icons ─────────────────────────────────────────────────────────────────
ico  = str(project_root / "app.ico")   if (project_root / "app.ico").exists()  else None
icns = str(project_root / "app.icns")  if (project_root / "app.icns").exists() else None

# ── Analysis ──────────────────────────────────────────────────────────────
a = Analysis(
    ["main.py"],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter", "unittest", "xmlrpc", "email", "html", "http",
        "urllib", "distutils", "test", "pydoc", "doctest",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="LapTest",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ico,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="LapTest",
)

# macOS only — produces LapTest.app bundle
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="LapTest.app",
        icon=icns,
        bundle_identifier="com.debeski.laptest",
        info_plist={
            "CFBundleShortVersionString": app_version,
            "CFBundleVersion":            app_version,
            "NSHighResolutionCapable":    True,
            "NSRequiresAquaSystemAppearance": False,
            # Required for macOS to show permission prompts
            "NSMicrophoneUsageDescription": "LapTest records a 3-second audio clip to verify the microphone works.",
            "NSCameraUsageDescription":     "LapTest opens the camera to verify the webcam works.",
        },
    )
