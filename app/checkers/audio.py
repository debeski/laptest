import platform
from app.checkers.base import CheckResult, Status
from app.utils.platform_utils import IS_WINDOWS, IS_MAC


def _wmi_audio_devices() -> list[dict]:
    if not IS_WINDOWS:
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
                "is_input": False,
            })
        return devices
    except Exception:
        return []


def _wmi_has_microphone() -> tuple[bool, str]:
    if not IS_WINDOWS:
        return False, "Not detected"
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


def _mac_audio_devices() -> tuple[list[dict], bool, str]:
    """
    Parse system_profiler SPAudioDataType on macOS.
    Returns (output_devices, mic_found, mic_name).
    """
    if not IS_MAC:
        return [], False, "Not detected"
    from app.utils.platform_utils import run_sp
    data = run_sp("SPAudioDataType", timeout=15)
    outputs  = []
    mic_found = False
    mic_name  = "Not detected"

    for section in data.get("SPAudioDataType", []):
        for item in section.get("_items", []):
            name = (item.get("_name") or "").strip()
            if not name:
                continue
            out_count = int(item.get("spdevice_output_source_count", 0) or 0)
            in_count  = int(item.get("spdevice_input_source_count", 0) or 0)
            mfr       = (item.get("spdevice_manufacturer") or "").strip()
            is_output = out_count > 0
            is_input  = in_count > 0

            if is_output:
                outputs.append({"name": name, "mfr": mfr, "status": "OK"})
            if is_input:
                mic_found = True
                mic_name  = name

    # sounddevice fallback: enumerate actual audio devices
    if not outputs and not mic_found:
        try:
            import sounddevice as sd
            devs = sd.query_devices()
            if not isinstance(devs, list):
                devs = [devs]
            for d in devs:
                name = d.get("name", "")
                if d.get("max_output_channels", 0) > 0:
                    outputs.append({"name": name, "mfr": "", "status": "OK"})
                if d.get("max_input_channels", 0) > 0 and not mic_found:
                    mic_found = True
                    mic_name  = name
        except Exception:
            pass

    return outputs, mic_found, mic_name


def run() -> list[CheckResult]:
    results = []

    if IS_WINDOWS:
        devices   = _wmi_audio_devices()
        mic_found, mic_name = _wmi_has_microphone()

        if devices:
            for d in devices:
                status = Status.PASS if d["status"] == "OK" else Status.WARN
                results.append(CheckResult(
                    key="audio_speakers",
                    label="Audio Device",
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

        results.append(CheckResult(
            key="audio_microphone",
            label="Microphone",
            value=mic_name if mic_found else "Not detected",
            status=Status.PASS if mic_found else Status.WARN,
            detail="Use the microphone test button to verify recording",
        ))

    elif IS_MAC:
        outputs, mic_found, mic_name = _mac_audio_devices()

        if outputs:
            for d in outputs:
                results.append(CheckResult(
                    key="audio_speakers",
                    label="Audio Output",
                    value=d["name"],
                    status=Status.PASS,
                ))
        else:
            results.append(CheckResult(
                key="audio_speakers",
                label="Audio Output",
                value="None detected",
                status=Status.WARN,
                detail="No output devices found — check System Settings → Sound",
            ))

        results.append(CheckResult(
            key="audio_microphone",
            label="Microphone",
            value=mic_name if mic_found else "Not detected",
            status=Status.PASS if mic_found else Status.WARN,
            detail="Grant Microphone permission in System Settings → Privacy & Security" if not mic_found else "",
        ))

    else:
        results.append(CheckResult(
            key="audio_speakers",
            label="Audio Devices",
            value="Not supported on this platform",
            status=Status.INFO,
        ))
        results.append(CheckResult(
            key="audio_microphone",
            label="Microphone",
            value="Not detected",
            status=Status.WARN,
        ))

    results.append(CheckResult(
        key="audio_speakers",
        label="Speaker Test",
        value="Use test button",
        status=Status.INFO,
        detail="Click 'Test Speakers' in the Audio tab to verify output",
    ))

    return results
