import platform
from app.checkers.base import CheckResult, Status
from app.utils.platform_utils import IS_WINDOWS, IS_MAC


# ── Windows backends ──────────────────────────────────────────────────────

def _detect_keyboard_win() -> tuple[bool, str]:
    try:
        import wmi
        c = wmi.WMI()
        kbs = list(c.Win32_Keyboard())
        if kbs:
            return True, (kbs[0].Name or "Standard Keyboard").strip()
    except Exception:
        pass
    return True, "Keyboard (assumed present)"


def _detect_touchpad_win() -> tuple[bool, str]:
    keywords_sets = [
        ["touchpad"], ["synaptics"], ["elan"], ["Alps"], ["precision touchpad"],
        ["hid-compliant mouse"], ["i2c hid"]
    ]
    try:
        import wmi
        c = wmi.WMI()
        for dev in c.Win32_PnPEntity():
            name = (dev.Name or "").lower()
            for kw_set in keywords_sets:
                if any(kw in name for kw in kw_set):
                    return True, (dev.Name or "").strip()
    except Exception:
        pass
    return False, "Not detected"


def _detect_fingerprint_win() -> tuple[bool, str]:
    try:
        import wmi
        c = wmi.WMI()
        for dev in c.Win32_PnPEntity():
            name = (dev.Name or "").lower()
            if "fingerprint" in name or "biometric" in name:
                return True, (dev.Name or "").strip()
    except Exception:
        pass
    return False, "Not detected"


# ── macOS backends ────────────────────────────────────────────────────────

def _detect_keyboard_mac() -> tuple[bool, str]:
    """On any MacBook, the built-in keyboard is always present."""
    from app.utils.platform_utils import run_command
    model = run_command(["sysctl", "-n", "hw.model"], timeout=5)
    if "MacBook" in model:
        return True, "Apple Internal Keyboard"
    return True, "Keyboard (assumed present)"


def _detect_touchpad_mac() -> tuple[bool, str]:
    """
    Detect the built-in trackpad via ioreg.
    All MacBooks have a Force Touch Trackpad since ~2015.
    """
    from app.utils.platform_utils import run_command
    out = run_command(["ioreg", "-r", "-c", "AppleMultitouchTrackpad", "-n", "AppleMultitouchTrackpad"], timeout=8)
    if out.strip():
        return True, "Apple Force Touch Trackpad"
    # Fall back: check for any HID trackpad
    out2 = run_command(["ioreg", "-r", "-c", "IOHIDDevice", "-a", "-d", "2"], timeout=10)
    if "trackpad" in out2.lower():
        return True, "Apple Trackpad"
    # All MacBooks have a trackpad — default to present
    model = run_command(["sysctl", "-n", "hw.model"], timeout=5)
    if "MacBook" in model:
        return True, "Apple Trackpad (assumed present)"
    return False, "Not detected"


def _detect_fingerprint_mac() -> tuple[bool, str]:
    """
    Touch ID is present on:
    - All Apple Silicon Macs (arm64)
    - Intel MacBooks with T2 chip (2018+)
    """
    if platform.machine() == "arm64":
        return True, "Touch ID (Apple Silicon)"
    from app.utils.platform_utils import run_sp
    data = run_sp("SPiBridgeDataType", timeout=10)
    if data.get("SPiBridgeDataType"):
        return True, "Touch ID (Apple T2 Security Chip)"
    return False, "Not present"


# ── Run ───────────────────────────────────────────────────────────────────

def run() -> list[CheckResult]:
    results = []

    if IS_WINDOWS:
        kb_found, kb_name = _detect_keyboard_win()
        tp_found, tp_name = _detect_touchpad_win()
        fp_found, fp_name = _detect_fingerprint_win()
    elif IS_MAC:
        kb_found, kb_name = _detect_keyboard_mac()
        tp_found, tp_name = _detect_touchpad_mac()
        fp_found, fp_name = _detect_fingerprint_mac()
    else:
        kb_found, kb_name = True, "Keyboard (assumed present)"
        tp_found, tp_name = False, "Not detected"
        fp_found, fp_name = False, "Not detected"

    results.append(CheckResult(
        key="input_keyboard",
        label="Keyboard",
        value=kb_name if kb_found else "Not detected",
        status=Status.PASS if kb_found else Status.FAIL,
        detail="Press each key in the Key Test to verify all keys work",
    ))

    results.append(CheckResult(
        key="input_touchpad",
        label="Touchpad",
        value=tp_name if tp_found else "Not detected",
        status=Status.PASS if tp_found else Status.WARN,
        detail="Touchpad driver not found" if not tp_found else "",
    ))

    results.append(CheckResult(
        key="input_fingerprint",
        label="Fingerprint Reader",
        value=fp_name if fp_found else "Not present",
        status=Status.INFO,
    ))

    results.append(CheckResult(
        key="input_key_test",
        label="Key Press Test",
        value="Use interactive test",
        status=Status.INFO,
        detail="Go to the Keyboard tab and press each key to confirm it registers",
    ))

    return results
