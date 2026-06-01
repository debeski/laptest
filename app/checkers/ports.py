import json
import platform
from app.checkers.base import CheckResult, Status
from app.utils.platform_utils import run_ps, IS_WINDOWS, IS_MAC


# ── Windows helpers ───────────────────────────────────────────────────────

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


def _display_outputs_win() -> dict:
    result = {"hdmi": 0, "dp": 0, "vga": 0, "monitors": 0}
    if not IS_WINDOWS:
        return result
    raw = run_ps(
        "Get-PnpDevice -Class Monitor -Status OK | Measure-Object | Select-Object -ExpandProperty Count",
        timeout=10,
    )
    try:
        result["monitors"] = int(raw.strip())
    except Exception:
        pass
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


def _sdcard_win() -> tuple[bool, str]:
    if not IS_WINDOWS:
        return False, ""
    raw = run_ps(
        "Get-PnpDevice -Status OK | Where-Object "
        "{$_.FriendlyName -match 'SD|MMC|Card Reader|Memory Card'} "
        "| Select-Object -First 1 -ExpandProperty FriendlyName",
        timeout=10,
    )
    return bool(raw.strip()), raw.strip()


def _audio_jack_win() -> bool:
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


# ── macOS helpers ─────────────────────────────────────────────────────────

def _flatten_usb_items(items: list) -> list[dict]:
    """Recursively flatten nested USB device tree."""
    flat = []
    for item in items:
        flat.append(item)
        for child in item.get("_items", []):
            flat.extend(_flatten_usb_items([child]))
    return flat


def _mac_usb_info() -> dict:
    """Return USB counts via system_profiler SPUSBDataType on macOS."""
    if not IS_MAC:
        return {}
    from app.utils.platform_utils import run_sp
    data = run_sp("SPUSBDataType", timeout=15)
    counts = {"usb2": 0, "usb3": 0, "usbc": 0, "thunderbolt": 0}
    for bus in data.get("SPUSBDataType", []):
        bus_name = bus.get("_name", "").lower()
        all_items = _flatten_usb_items(bus.get("_items", []))
        speed_str = bus.get("host_controller", "") or ""
        # Count the bus itself
        if "3.1" in bus_name or "3.0" in bus_name or "3.2" in bus_name or "xhci" in bus_name:
            counts["usb3"] += 1
        elif "2.0" in bus_name or "ehci" in bus_name or "uhci" in bus_name:
            counts["usb2"] += 1
        # Scan items for speed info
        for item in all_items:
            s = (item.get("speed") or "").lower()
            n = (item.get("_name") or "").lower()
            if "10 gigabit" in s or "20 gigabit" in s or "superspeed" in s:
                counts["usb3"] += 1
            elif "usb-c" in n or "type-c" in n:
                counts["usbc"] += 1

    return counts


def _mac_thunderbolt_info() -> dict:
    """Return Thunderbolt info via system_profiler SPThunderboltDataType."""
    if not IS_MAC:
        return {}
    from app.utils.platform_utils import run_sp
    data = run_sp("SPThunderboltDataType", timeout=15)
    result = {"ports": 0, "version": ""}
    for bus in data.get("SPThunderboltDataType", []):
        ports = bus.get("spthunderbolt_num_ports", "")
        uid   = bus.get("spthunderbolt_uid", "") or ""
        try:
            result["ports"] = int(ports)
        except Exception:
            if data.get("SPThunderboltDataType"):
                result["ports"] = len(data["SPThunderboltDataType"])
        if "4" in uid or "thunderbolt 4" in str(bus).lower():
            result["version"] = "Thunderbolt 4"
        elif "3" in uid:
            result["version"] = "Thunderbolt 3"
        else:
            result["version"] = "Thunderbolt"
        break
    return result


def _mac_sdcard() -> tuple[bool, str]:
    if not IS_MAC:
        return False, ""
    from app.utils.platform_utils import run_sp
    data = run_sp("SPCardReaderDataType", timeout=10)
    entries = data.get("SPCardReaderDataType", [])
    if entries:
        name = entries[0].get("_name", "SD Card Reader")
        return True, name
    return False, ""


def _mac_audio_jack() -> bool:
    """Detect audio jack via system_profiler SPAudioDataType on macOS."""
    if not IS_MAC:
        return False
    from app.utils.platform_utils import run_sp
    data = run_sp("SPAudioDataType", timeout=10)
    for entry in data.get("SPAudioDataType", []):
        for item in entry.get("_items", []):
            name = (item.get("_name") or "").lower()
            if "headphone" in name or "line out" in name or "audio line" in name or "combo" in name:
                return True
    return False


# ── Run ───────────────────────────────────────────────────────────────────

def run() -> list[CheckResult]:
    results = []

    if IS_WINDOWS:
        usb_names = _usb_devices()
        usb = _parse_usb(usb_names)
        disp = _display_outputs_win()
        total_usb = usb["usb3"] + usb["usb2"] + usb["usb_c"] + usb["thunderbolt"]

        if usb["usb3"]:
            results.append(CheckResult(
                key="ports_usb3", label="USB 3.x Controllers",
                value=str(usb["usb3"]), status=Status.PASS,
            ))
        if usb["usb2"]:
            results.append(CheckResult(
                key="ports_usb2", label="USB 2.0 Controllers",
                value=str(usb["usb2"]), status=Status.INFO,
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

        sd_found, sd_name = _sdcard_win()
        results.append(CheckResult(
            key="ports_sdcard", label="SD Card Reader",
            value=sd_name if sd_found else "Not detected",
            status=Status.INFO,
        ))

        jack = _audio_jack_win()
        results.append(CheckResult(
            key="ports_audio_jack", label="Audio Jack",
            value="Detected" if jack else "Not detected",
            status=Status.INFO,
        ))

    elif IS_MAC:
        tb = _mac_thunderbolt_info()
        usb = _mac_usb_info()

        if tb.get("ports", 0) > 0:
            label = tb.get("version") or "Thunderbolt"
            results.append(CheckResult(
                key="ports_usbc", label=label,
                value=f"{tb['ports']} port(s)",
                status=Status.PASS,
            ))
        if usb.get("usb3", 0) > 0:
            results.append(CheckResult(
                key="ports_usb3", label="USB 3.x",
                value=str(usb["usb3"]),
                status=Status.PASS,
            ))
        if usb.get("usbc", 0) > 0:
            results.append(CheckResult(
                key="ports_usbc", label="USB-C",
                value=str(usb["usbc"]),
                status=Status.PASS,
            ))
        if usb.get("usb2", 0) > 0:
            results.append(CheckResult(
                key="ports_usb2", label="USB 2.0",
                value=str(usb["usb2"]),
                status=Status.INFO,
            ))
        if not tb.get("ports") and not usb.get("usb3") and not usb.get("usbc"):
            results.append(CheckResult(
                key="ports_usb", label="USB / Thunderbolt",
                value="Could not enumerate — try running as administrator",
                status=Status.INFO,
            ))

        # Video outputs on macOS are via Thunderbolt/USB-C — report informational
        results.append(CheckResult(
            key="ports_hdmi", label="Video Output",
            value="Via Thunderbolt / USB-C ports",
            status=Status.INFO,
        ))

        sd_found, sd_name = _mac_sdcard()
        results.append(CheckResult(
            key="ports_sdcard", label="SD Card Reader",
            value=sd_name if sd_found else "Not detected",
            status=Status.INFO,
        ))

        jack = _mac_audio_jack()
        results.append(CheckResult(
            key="ports_audio_jack", label="Audio Jack (3.5 mm)",
            value="Detected" if jack else "Not detected",
            status=Status.INFO,
        ))

    else:
        results.append(CheckResult(
            key="ports_usb", label="USB Ports",
            value="Not supported on this platform", status=Status.INFO,
        ))

    return results
