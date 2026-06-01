import platform
import psutil
from app.checkers.base import CheckResult, Status


def _wmi_network() -> list[dict]:
    if platform.system() != "Windows":
        return []
    try:
        import wmi
        c = wmi.WMI()
        adapters = []
        for nic in c.Win32_NetworkAdapter():
            if not nic.PhysicalAdapter:
                continue
            name = (nic.Name or "").strip()
            adapters.append({
                "name":    name,
                "mac":     (nic.MACAddress or "").strip(),
                "speed":   int(nic.Speed or 0),
                "type":    _classify_adapter(name),
                "status":  (nic.NetConnectionStatus or -1),
            })
        return adapters
    except Exception:
        return []


_NIC_STATUS = {
    0: "Disconnected", 1: "Connecting", 2: "Connected",
    3: "Disconnecting", 4: "Hardware not present",
    5: "Hardware disabled", 7: "Media disconnected",
}


def _classify_adapter(name: str) -> str:
    n = name.lower()
    if "wi-fi" in n or "wireless" in n or "wlan" in n or "802.11" in n:
        return "wifi"
    if "ethernet" in n or "gigabit" in n or "realtek" in n and "pci" in n:
        return "ethernet"
    if "bluetooth" in n:
        return "bluetooth"
    return "other"


def _wifi_standard(name: str) -> str:
    n = name.lower()
    if "wi-fi 7" in n or "be" in n:
        return "Wi-Fi 7 (802.11be)"
    if "wi-fi 6e" in n or "ax" in n and "6e" in n:
        return "Wi-Fi 6E (802.11ax)"
    if "wi-fi 6" in n or "ax" in n:
        return "Wi-Fi 6 (802.11ax)"
    if "wi-fi 5" in n or "ac" in n:
        return "Wi-Fi 5 (802.11ac)"
    if "wi-fi 4" in n or "802.11n" in n:
        return "Wi-Fi 4 (802.11n)"
    return "Unknown standard"


def run() -> list[CheckResult]:
    results = []
    adapters = _wmi_network()

    wifi = [a for a in adapters if a["type"] == "wifi"]
    eth  = [a for a in adapters if a["type"] == "ethernet"]
    bt   = [a for a in adapters if a["type"] == "bluetooth"]

    if wifi:
        w = wifi[0]
        connected = w["status"] == 2
        results.append(CheckResult(
            key="network_wifi",
            label="Wi-Fi",
            value=w["name"],
            status=Status.PASS if connected else Status.WARN,
            detail=_NIC_STATUS.get(w["status"], ""),
        ))
        std = _wifi_standard(w["name"])
        results.append(CheckResult(
            key="network_wifi_std",
            label="Wi-Fi Standard",
            value=std,
            status=Status.PASS if "6" in std or "7" in std else Status.WARN,
            detail="Wi-Fi 4/5 may limit speeds on modern networks" if "4" in std or "5" in std else "",
        ))
        if w["mac"]:
            results.append(CheckResult(
                key="network_mac", label="Wi-Fi MAC", value=w["mac"], status=Status.INFO,
            ))
    else:
        results.append(CheckResult(
            key="network_wifi", label="Wi-Fi",
            value="Not detected", status=Status.WARN,
            detail="No Wi-Fi adapter found"
        ))

    if eth:
        e = eth[0]
        connected = e["status"] == 2
        speed_mbps = e["speed"] / 1_000_000 if e["speed"] else 0
        results.append(CheckResult(
            key="network_ethernet",
            label="Ethernet",
            value=f"{e['name']}{f' ({speed_mbps:.0f} Mbps)' if speed_mbps else ''}",
            status=Status.INFO,
        ))
    else:
        results.append(CheckResult(
            key="network_ethernet", label="Ethernet",
            value="Not detected", status=Status.INFO,
        ))

    if bt:
        results.append(CheckResult(
            key="network_bluetooth", label="Bluetooth",
            value=bt[0]["name"], status=Status.PASS,
        ))
    else:
        bt_detected = False
        if platform.system() == "Windows":
            try:
                import wmi
                c = wmi.WMI()
                for dev in c.Win32_PnPEntity():
                    if "bluetooth" in (dev.Name or "").lower():
                        bt_detected = True
                        break
            except Exception:
                pass
        results.append(CheckResult(
            key="network_bluetooth", label="Bluetooth",
            value="Detected" if bt_detected else "Not detected",
            status=Status.PASS if bt_detected else Status.WARN,
        ))

    return results
