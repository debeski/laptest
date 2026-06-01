import platform
from app.checkers.base import CheckResult, Status


def _wmi_audio_devices() -> list[dict]:
    if platform.system() != "Windows":
        return []
    try:
        import wmi
        c = wmi.WMI()
        devices = []
        for d in c.Win32_SoundDevice():
            devices.append({
                "name":   (d.Name or "").strip(),
                "status": (d.Status or "").strip(),
                "mfr":    (d.Manufacturer or "").strip(),
            })
        return devices
    except Exception:
        return []


def _has_microphone() -> tuple[bool, str]:
    if platform.system() == "Windows":
        try:
            import wmi
            c = wmi.WMI()
            for dev in c.Win32_PnPEntity():
                name = (dev.Name or "").lower()
                if "microphone" in name or "mic array" in name:
                    return True, (dev.Name or "").strip()
        except Exception:
            pass
    return False, "Not detected"


def run() -> list[CheckResult]:
    results = []
    devices = _wmi_audio_devices()

    if devices:
        for d in devices:
            status = Status.PASS if d["status"] == "OK" else Status.WARN
            results.append(CheckResult(
                key="audio_speakers",
                label=f"Audio Device",
                value=d["name"],
                status=status,
                detail=f"Status: {d['status']}" if d["status"] != "OK" else "",
            ))
    else:
        results.append(CheckResult(
            key="audio_speakers",
            label="Audio Devices",
            value="None detected",
            status=Status.WARN,
            detail="No audio devices found — check drivers",
        ))

    mic_found, mic_name = _has_microphone()
    results.append(CheckResult(
        key="audio_microphone",
        label="Microphone",
        value=mic_name if mic_found else "Not detected",
        status=Status.PASS if mic_found else Status.WARN,
        detail="Use the microphone test button to verify recording",
    ))

    results.append(CheckResult(
        key="audio_speakers",
        label="Speaker Test",
        value="Use test button",
        status=Status.INFO,
        detail="Click 'Test Speakers' in the Audio tab to verify output",
    ))

    return results
