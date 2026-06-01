import math
import platform
from app.checkers.base import CheckResult, Status


def _screen_info() -> list[dict]:
    try:
        from PyQt6.QtWidgets import QApplication
        screens = []
        app = QApplication.instance()
        if app:
            for s in app.screens():
                geom = s.geometry()
                mm = s.physicalSize()
                dpr = s.devicePixelRatio()
                w_px = geom.width() * dpr
                h_px = geom.height() * dpr
                diag_mm = math.sqrt(mm.width() ** 2 + mm.height() ** 2) if mm.width() > 0 else 0
                diag_in = diag_mm / 25.4 if diag_mm > 0 else 0
                ppi = math.sqrt(w_px ** 2 + h_px ** 2) / diag_in if diag_in > 0 else 0
                screens.append({
                    "name":    s.name(),
                    "width":   int(w_px),
                    "height":  int(h_px),
                    "refresh": s.refreshRate(),
                    "dpi":     s.physicalDotsPerInch(),
                    "ppi":     ppi,
                    "diag_in": diag_in,
                    "dpr":     dpr,
                })
        return screens
    except Exception:
        return []


def _wmi_display_info() -> dict:
    if platform.system() != "Windows":
        return {}
    try:
        import wmi
        c = wmi.WMI()
        monitors = list(c.Win32_DesktopMonitor())
        if monitors:
            m = monitors[0]
            return {
                "name":       (m.Name or "").strip(),
                "caption":    (m.Caption or "").strip(),
                "screen_h":   int(m.ScreenHeight or 0),
                "screen_w":   int(m.ScreenWidth or 0),
                "pixels_per_xlogical": int(m.PixelsPerXLogicalInch or 0),
            }
    except Exception:
        pass
    return {}


def _touch_capable() -> bool:
    if platform.system() == "Windows":
        try:
            import wmi
            c = wmi.WMI()
            for dev in c.Win32_PnPEntity():
                name = (dev.Name or "").lower()
                if "touch" in name and ("screen" in name or "digitizer" in name):
                    return True
        except Exception:
            pass
    return False


def run() -> list[CheckResult]:
    results = []
    screens = _screen_info()

    if not screens:
        results.append(CheckResult(
            key="display_resolution", label="Display",
            value="Could not detect", status=Status.INFO
        ))
        return results

    for i, s in enumerate(screens):
        pfx = f"Screen {i + 1}: " if len(screens) > 1 else ""
        w, h = s["width"], s["height"]

        res_status = Status.PASS if w >= 1920 else (Status.WARN if w >= 1366 else Status.FAIL)
        results.append(CheckResult(
            key="display_resolution",
            label=f"{pfx}Resolution",
            value=f"{w} × {h}",
            status=res_status,
            detail="1366×768 is low resolution for modern use" if w < 1600 else "",
        ))

        refresh = s["refresh"]
        r_status = Status.PASS if refresh >= 60 else Status.FAIL
        results.append(CheckResult(
            key="display_refresh",
            label=f"{pfx}Refresh Rate",
            value=f"{refresh:.0f} Hz",
            status=r_status,
        ))

        ppi = s["ppi"]
        if ppi > 0:
            p_status = Status.PASS if ppi >= 130 else (Status.WARN if ppi >= 96 else Status.FAIL)
            results.append(CheckResult(
                key="display_ppi",
                label=f"{pfx}Pixel Density",
                value=f"{ppi:.0f} PPI",
                status=p_status,
                detail="Low pixel density — screen may look pixelated" if ppi < 96 else "",
            ))

        diag = s["diag_in"]
        if diag > 0:
            results.append(CheckResult(
                key="display_size",
                label=f"{pfx}Screen Size",
                value=f'{diag:.1f}"',
                status=Status.INFO,
            ))

    touch = _touch_capable()
    results.append(CheckResult(
        key="display_touch",
        label="Touch Screen",
        value="Yes" if touch else "No",
        status=Status.INFO,
    ))

    results.append(CheckResult(
        key="display_dead_pixels",
        label="Dead Pixel Test",
        value="Manual test required",
        status=Status.INFO,
        detail="Use the dead pixel test in the Display tab to check visually",
    ))

    return results
