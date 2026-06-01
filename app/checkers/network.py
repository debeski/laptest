import platform
import psutil
from app.checkers.base import CheckResult, Status
from app.utils.platform_utils import IS_WINDOWS, IS_MAC


def _wmi_network() -> list[dict]:
    if not IS_WINDOWS:
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
                "name":   name,
                "mac":    (nic.MACAddress or "").strip(),
                "speed":  int(nic.Speed or 0),
                "type":   _classify_adapter(name),
                "status": (nic.NetConnectionStatus or -1),
            })
        return adapters
    except Exception:
        return []


def _mac_network() -> dict:
    """Return network info dict via system_profiler on macOS."""
    if not IS_MAC:
        return {}
    from app.utils.platform_utils import run_sp
    result = {"wifi": None, "ethernet": [], "bluetooth": False}

    # Wi-Fi info
    airport = run_sp("SPAirPortDataType", timeout=15)
    for entry in airport.get("SPAirPortDataType", []):
        card_type = entry.get("spairport_wireless_card_type", "")
        current = entry.get("spairport_current-network-information", {})
        phymode = current.get("spairport_current_network_phymode", "")
        ssid    = current.get("_name", "")
        result["wifi"] = {
            "name":    card_type or "AirPort",
            "ssid":    ssid,
            "phymode": phymode,
            "connected": bool(ssid),
        }
        break

    # General network: check for ethernet interfaces
    net_data = run_sp("SPNetworkDataType", timeout=15)
    for entry in net_data.get("SPNetworkDataType", []):
        hw = entry.get("hardware", "").lower()
        iface = entry.get("interface", "")
        name  = entry.get("_name", "")
        if "ethernet" in hw or "ethernet" in name.lower():
            result["ethernet"].append({
                "name":  name,
                "iface": iface,
            })
        if hw == "bluetooth" or "bluetooth" in name.lower():
            result["bluetooth"] = True

    # Bluetooth from dedicated profiler
    if not result["bluetooth"]:
        bt_data = run_sp("SPBluetoothDataType", timeout=10)
        for entry in bt_data.get("SPBluetoothDataType", []):
            ctrl = entry.get("controller_properties", {})
            if ctrl.get("controller_state", "").lower() in ("attrib_on", "enabled", "on"):
                result["bluetooth"] = True
                break
            if "controller_address" in ctrl:
                result["bluetooth"] = True
                break

    return result


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


def _wifi_standard_from_name(name: str) -> str:
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


def _wifi_standard_from_phymode(phymode: str) -> str:
    p = phymode.lower()
    if "be" in p or "802.11be" in p:
        return "Wi-Fi 7 (802.11be)"
    if "6e" in p:
        return "Wi-Fi 6E (802.11ax)"
    if "ax" in p or "802.11ax" in p:
        return "Wi-Fi 6 (802.11ax)"
    if "ac" in p or "802.11ac" in p:
        return "Wi-Fi 5 (802.11ac)"
    if "n" in p or "802.11n" in p:
        return "Wi-Fi 4 (802.11n)"
    if phymode:
        return phymode
    return "Unknown standard"


def run() -> list[CheckResult]:
    results = []

    if IS_WINDOWS:
        adapters = _wmi_network()
        wifi = [a for a in adapters if a["type"] == "wifi"]
        eth  = [a for a in adapters if a["type"] == "ethernet"]
        bt   = [a for a in adapters if a["type"] == "bluetooth"]

        if wifi:
            w = wifi[0]
            connected = w["status"] == 2
            results.append(CheckResult(
                key="network_wifi", label="Wi-Fi",
                value=w["name"],
                status=Status.PASS if connected else Status.WARN,
                detail=_NIC_STATUS.get(w["status"], ""),
            ))
            std = _wifi_standard_from_name(w["name"])
            results.append(CheckResult(
                key="network_wifi_std", label="Wi-Fi Standard",
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
            speed_mbps = e["speed"] / 1_000_000 if e["speed"] else 0
            results.append(CheckResult(
                key="network_ethernet", label="Ethernet",
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

    elif IS_MAC:
        mac_net = _mac_network()

        wifi = mac_net.get("wifi")
        if wifi:
            ssid  = wifi["ssid"]
            label = f'{wifi["name"]} — connected to "{ssid}"' if ssid else wifi["name"]
            results.append(CheckResult(
                key="network_wifi", label="Wi-Fi",
                value=label,
                status=Status.PASS if wifi["connected"] else Status.WARN,
                detail="" if wifi["connected"] else "Wi-Fi not connected to a network",
            ))
            std = _wifi_standard_from_phymode(wifi.get("phymode", ""))
            results.append(CheckResult(
                key="network_wifi_std", label="Wi-Fi Standard",
                value=std,
                status=Status.PASS if "6" in std or "7" in std else Status.WARN,
                detail="Wi-Fi 4/5 may limit speeds on modern networks" if "4" in std or "5" in std else "",
            ))
        else:
            results.append(CheckResult(
                key="network_wifi", label="Wi-Fi",
                value="Not detected", status=Status.WARN,
                detail="No AirPort adapter found"
            ))

        eth = mac_net.get("ethernet", [])
        if eth:
            results.append(CheckResult(
                key="network_ethernet", label="Ethernet",
                value=eth[0]["name"], status=Status.INFO,
            ))
        else:
            results.append(CheckResult(
                key="network_ethernet", label="Ethernet",
                value="Not detected", status=Status.INFO,
            ))

        bt_found = mac_net.get("bluetooth", False)
        results.append(CheckResult(
            key="network_bluetooth", label="Bluetooth",
            value="Detected" if bt_found else "Not detected",
            status=Status.PASS if bt_found else Status.WARN,
        ))

    else:
        results.append(CheckResult(
            key="network_wifi", label="Wi-Fi", value="Not detected", status=Status.WARN,
        ))
        results.append(CheckResult(
            key="network_ethernet", label="Ethernet", value="Not detected", status=Status.INFO,
        ))
        results.append(CheckResult(
            key="network_bluetooth", label="Bluetooth", value="Not detected", status=Status.WARN,
        ))

    return results
