import platform
from app.checkers.base import CheckResult, Status


def _detect_device(keywords: list[str]) -> tuple[bool, str]:
    if platform.system() != "Windows":
        return False, ""
    try:
        import wmi
        c = wmi.WMI()
        for dev in c.Win32_PnPEntity():
            name = (dev.Name or "").lower()
            if all(k.lower() in name for k in keywords[:1]):
                if any(k.lower() in name for k in keywords[1:]):
                    return True, (dev.Name or "").strip()
        for dev in c.Win32_PnPEntity():
            name = (dev.Name or "").lower()
            caption = (dev.Caption or "").lower()
            for k in keywords:
                if k.lower() in name or k.lower() in caption:
                    return True, (dev.Name or dev.Caption or "").strip()
    except Exception:
        pass
    return False, ""


def _detect_keyboard() -> tuple[bool, str]:
    if platform.system() == "Windows":
        try:
            import wmi
            c = wmi.WMI()
            kbs = list(c.Win32_Keyboard())
            if kbs:
                return True, (kbs[0].Name or "Standard Keyboard").strip()
        except Exception:
            pass
    return True, "Keyboard (assumed present)"


def _detect_touchpad() -> tuple[bool, str]:
    keywords_sets = [
        ["touchpad"], ["synaptics"], ["elan"], ["Alps"], ["precision touchpad"],
        ["hid-compliant mouse"], ["i2c hid"]
    ]
    if platform.system() == "Windows":
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


def _detect_fingerprint() -> tuple[bool, str]:
    if platform.system() == "Windows":
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


def run() -> list[CheckResult]:
    results = []

    kb_found, kb_name = _detect_keyboard()
    results.append(CheckResult(
        key="input_keyboard",
        label="Keyboard",
        value=kb_name if kb_found else "Not detected",
        status=Status.PASS if kb_found else Status.FAIL,
        detail="Press each key in the Key Test to verify all keys work",
    ))

    tp_found, tp_name = _detect_touchpad()
    results.append(CheckResult(
        key="input_touchpad",
        label="Touchpad",
        value=tp_name if tp_found else "Not detected",
        status=Status.PASS if tp_found else Status.WARN,
        detail="Touchpad driver not found" if not tp_found else "",
    ))

    fp_found, fp_name = _detect_fingerprint()
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
