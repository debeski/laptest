import json
import platform
from app.checkers.base import CheckResult, Status
from app.utils.platform_utils import run_ps, IS_WINDOWS


def _usb_devices() -> list[str]:
    """Return friendly names of all OK USB PnP devices."""
    if not IS_WINDOWS:
        return []
    raw = run_ps(
        "Get-PnpDevice -Class USB -Status OK "
        "| Select-Object -ExpandProperty FriendlyName",
        timeout=15,
    )
    return [l.strip() for l in raw.splitlines() if l.strip()]


def _parse_usb(names: list[str]) -> dict:
    counts = {"usb2": 0, "usb3": 0, "usb_c": 0, "thunderbolt": 0, "names": []}
    for n in names:
        nl = n.lower()
        if "thunderbolt" in nl:
            counts["thunderbolt"] += 1
            counts["names"].append(n)
        elif "usb-c" in nl or "type-c" in nl or "type c" in nl:
            counts["usb_c"] += 1
            counts["names"].append(n)
        elif any(x in nl for x in ("xhci", "3.2", "3.1", "3.0", "superspeed", "usb 3")):
            counts["usb3"] += 1
            counts["names"].append(n)
        elif any(x in nl for x in ("uhci", "ohci", "ehci", "2.0", "usb 2", "high speed")):
            counts["usb2"] += 1
    return counts


def _display_outputs() -> dict:
    """Detect display outputs (HDMI, DisplayPort, VGA) from PnP and video controllers."""
    result = {"hdmi": 0, "dp": 0, "vga": 0, "monitors": 0}
    if not IS_WINDOWS:
        return result
    # Count connected monitors
    raw = run_ps(
        "Get-PnpDevice -Class Monitor -Status OK | Measure-Object | Select-Object -ExpandProperty Count",
        timeout=10,
    )
    try:
        result["monitors"] = int(raw.strip())
    except Exception:
        pass
    # Check for HDMI/DP in audio device names (HDMI audio = HDMI port present)
    raw2 = run_ps(
        "Get-PnpDevice -Status OK | Where-Object {$_.FriendlyName -match 'HDMI|DisplayPort|VGA'} "
        "| Select-Object -ExpandProperty FriendlyName",
        timeout=12,
    )
    for line in raw2.splitlines():
        ll = line.lower()
        if "hdmi" in ll:
            result["hdmi"] += 1
        if "displayport" in ll or "display port" in ll:
            result["dp"] += 1
        if "vga" in ll:
            result["vga"] += 1
    return result


def _sdcard() -> tuple[bool, str]:
    if not IS_WINDOWS:
        return False, ""
    raw = run_ps(
        "Get-PnpDevice -Status OK | Where-Object "
        "{$_.FriendlyName -match 'SD|MMC|Card Reader|Memory Card'} "
        "| Select-Object -First 1 -ExpandProperty FriendlyName",
        timeout=10,
    )
    return bool(raw.strip()), raw.strip()


def _audio_jack() -> bool:
    if not IS_WINDOWS:
        return False
    raw = run_ps(
        "Get-PnpDevice -Status OK | Where-Object "
        "{$_.FriendlyName -match 'Audio|Realtek|High Definition'} "
        "| Measure-Object | Select-Object -ExpandProperty Count",
        timeout=10,
    )
    try:
        return int(raw.strip()) > 0
    except Exception:
        return False


def run() -> list[CheckResult]:
    results = []

    usb_names = _usb_devices()
    usb = _parse_usb(usb_names)
    disp = _display_outputs()

    total_usb = usb["usb3"] + usb["usb2"] + usb["usb_c"] + usb["thunderbolt"]

    if usb["usb3"]:
        results.append(CheckResult(
            key="ports_usb3", label="USB 3.x Controllers",
            value=str(usb["usb3"]),
            status=Status.PASS,
        ))
    if usb["usb2"]:
        results.append(CheckResult(
            key="ports_usb2", label="USB 2.0 Controllers",
            value=str(usb["usb2"]),
            status=Status.INFO,
        ))
    if usb["usb_c"]:
        results.append(CheckResult(
            key="ports_usbc", label="USB-C",
            value=str(usb["usb_c"]), status=Status.PASS,
        ))
    if usb["thunderbolt"]:
        results.append(CheckResult(
            key="ports_usbc", label="Thunderbolt",
            value=str(usb["thunderbolt"]), status=Status.PASS,
        ))
    if total_usb == 0:
        results.append(CheckResult(
            key="ports_usb", label="USB Ports",
            value="Could not enumerate — try running as administrator",
            status=Status.INFO,
        ))

    # Display outputs
    if disp["monitors"] > 0:
        results.append(CheckResult(
            key="ports_hdmi", label="Connected Monitors",
            value=str(disp["monitors"]), status=Status.INFO,
        ))
    if disp["hdmi"]:
        results.append(CheckResult(
            key="ports_hdmi", label="HDMI",
            value=str(disp["hdmi"]), status=Status.INFO,
        ))
    if disp["dp"]:
        results.append(CheckResult(
            key="ports_hdmi", label="DisplayPort",
            value=str(disp["dp"]), status=Status.INFO,
        ))
    if disp["vga"]:
        results.append(CheckResult(
            key="ports_hdmi", label="VGA",
            value=str(disp["vga"]), status=Status.INFO,
        ))
    if not any([disp["hdmi"], disp["dp"], disp["vga"]]):
        results.append(CheckResult(
            key="ports_hdmi", label="Video Outputs",
            value="Not enumerated via PnP — check GPU specs",
            status=Status.INFO,
        ))

    sd_found, sd_name = _sdcard()
    results.append(CheckResult(
        key="ports_sdcard", label="SD Card Reader",
        value=sd_name if sd_found else "Not detected",
        status=Status.INFO,
    ))

    jack = _audio_jack()
    results.append(CheckResult(
        key="ports_audio_jack", label="Audio Jack",
        value="Detected" if jack else "Not detected",
        status=Status.INFO,
    ))

    return results
