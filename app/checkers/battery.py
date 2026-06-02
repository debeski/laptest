import platform
import psutil
from app.checkers.base import CheckResult, Status
from app.utils.formatters import fmt_duration, fmt_voltage
from app.utils.platform_utils import IS_WINDOWS, IS_MAC


# ── Windows backends ──────────────────────────────────────────────────────

def _wmi_battery() -> dict:
    if not IS_WINDOWS:
        return {}
    try:
        import wmi
        c = wmi.WMI()
        for b in c.Win32_Battery():
            return {
                "name":            (b.Name or "").strip(),
                "manufacturer":    (b.Manufacturer or "").strip(),
                "design_capacity": int(b.DesignCapacity or 0),
                "full_capacity":   int(b.FullChargeCapacity or 0),
                "status":          int(b.BatteryStatus or 0),
                "chemistry":       int(b.Chemistry or 0),
                "voltage":         int(b.DesignVoltage or 0) / 1000,
            }
    except Exception:
        pass
    return {}


def _wmi_battery_static() -> dict:
    if not IS_WINDOWS:
        return {}
    try:
        import wmi
        c = wmi.WMI(namespace="root/wmi")
        for b in c.BatteryStaticData():
            return {
                "cycle_count":     int(b.CycleCount or 0),
                "design_capacity": int(b.DesignedCapacity or 0),
            }
    except Exception:
        pass
    return {}


def _wmi_battery_full_cap() -> int:
    if not IS_WINDOWS:
        return 0
    try:
        import wmi
        c = wmi.WMI(namespace="root/wmi")
        for b in c.BatteryFullChargedCapacity():
            return int(b.FullChargedCapacity or 0)
    except Exception:
        pass
    return 0


# ── macOS backend ─────────────────────────────────────────────────────────

def _mac_battery_detail() -> dict:
    """
    Read battery detail from IOKit via ioreg on macOS.
    Returns a dict with design_capacity, max_capacity (mAh), cycle_count, etc.
    """
    if not IS_MAC:
        return {}
    import plistlib
    from app.utils.platform_utils import run_command
    out = run_command(["ioreg", "-r", "-c", "AppleSmartBattery", "-a"], timeout=10)
    if not out:
        return {}
    try:
        data = plistlib.loads(out.encode())
        if isinstance(data, list) and data:
            b = data[0]
        elif isinstance(data, dict):
            b = data
        else:
            return {}
        # On Apple Silicon, MaxCapacity may be 100 (a % scale, not mAh).
        # AppleRawMaxCapacity is always in mAh — prefer it.
        raw_max = b.get("AppleRawMaxCapacity") or b.get("AppleMaxCapacity")
        max_cap = int(raw_max) if raw_max is not None else int(b.get("MaxCapacity", 0))
        design  = int(b.get("DesignCapacity", 0))

        # Sanity check: if max_cap looks like a percentage (≤ 100) but design > 1000,
        # MaxCapacity is a percent scale — cannot compute meaningful mAh health.
        if max_cap <= 100 and design > 500:
            max_cap = 0  # skip health calculation; avoid the 1.6% bug

        return {
            "design_capacity":  design,
            "max_capacity":     max_cap,
            "current_capacity": int(b.get("AppleRawCurrentCapacity") or b.get("CurrentCapacity") or 0),
            "cycle_count":      int(b.get("CycleCount", 0)),
            "temperature":      b.get("Temperature"),   # units: 0.01 °C
            "is_charging":      bool(b.get("IsCharging", False)),
            "external":         bool(b.get("ExternalConnected", False)),
            "fully_charged":    bool(b.get("FullyCharged", False)),
            "voltage_mv":       int(b.get("Voltage", 0)),
            "manufacturer":     str(b.get("Manufacturer", "") or ""),
        }
    except Exception:
        return {}


# ── Shared maps ───────────────────────────────────────────────────────────

_STATUS_MAP = {
    1: "Discharging", 2: "AC Connected", 3: "Fully Charged",
    4: "Low", 5: "Critical", 6: "Charging", 7: "Charging High",
    8: "Charging Low", 9: "Charging Critical", 10: "Undefined",
    11: "Partially Charged",
}
_CHEMISTRY_MAP = {
    1: "Other", 2: "Unknown", 3: "Lead Acid", 4: "Nickel Cadmium",
    5: "Nickel Metal Hydride", 6: "Lithium-ion", 7: "Zinc Air",
    8: "Lithium Polymer",
}


def run() -> list[CheckResult]:
    results = []
    bat = psutil.sensors_battery()

    if bat is None:
        results.append(CheckResult(
            key="battery_status", label="Battery",
            value="No battery detected", status=Status.INFO,
            detail="This may be a desktop or the battery is not connected"
        ))
        return results

    charge  = bat.percent
    plugged = bat.power_plugged
    secs    = bat.secsleft

    results.append(CheckResult(
        key="battery_status", label="Status",
        value=("Plugged in" if plugged else "On battery"),
        status=Status.INFO,
    ))
    results.append(CheckResult(
        key="battery_health", label="Charge Level",
        value=f"{charge:.0f}%",
        status=Status.PASS if charge > 20 else (Status.WARN if charge > 10 else Status.FAIL),
    ))

    if secs and secs > 0:
        results.append(CheckResult(
            key="battery_time", label="Time Remaining",
            value=fmt_duration(secs),
            status=Status.PASS if secs > 3600 else (Status.WARN if secs > 1800 else Status.FAIL),
        ))

    if IS_WINDOWS:
        wmi_bat    = _wmi_battery()
        static     = _wmi_battery_static()
        full_cap   = _wmi_battery_full_cap()
        design_cap = wmi_bat.get("design_capacity") or static.get("design_capacity") or 0
        full_cap   = full_cap or wmi_bat.get("full_capacity") or 0

        if design_cap > 0 and full_cap > 0:
            wear       = 100.0 * (1 - full_cap / design_cap)
            health_pct = 100.0 * full_cap / design_cap
            h_status   = (Status.PASS if health_pct >= 80
                          else Status.WARN if health_pct >= 50
                          else Status.FAIL)
            results.append(CheckResult(
                key="battery_health", label="Battery Health",
                value=f"{health_pct:.1f}%", status=h_status,
                detail="Battery has significant wear — replacement recommended" if health_pct < 60 else "",
            ))
            results.append(CheckResult(
                key="battery_wear", label="Wear Level",
                value=f"{wear:.1f}%", status=h_status,
            ))
            results.append(CheckResult(
                key="battery_capacity", label="Full Capacity",
                value=f"{full_cap} mWh", status=Status.INFO,
            ))
            results.append(CheckResult(
                key="battery_design", label="Design Capacity",
                value=f"{design_cap} mWh", status=Status.INFO,
            ))

        cycles = static.get("cycle_count", 0)
        if cycles:
            c_status = Status.PASS if cycles < 300 else (Status.WARN if cycles < 600 else Status.FAIL)
            results.append(CheckResult(
                key="battery_cycles", label="Charge Cycles",
                value=str(cycles), status=c_status,
                detail="High cycle count indicates significant battery age" if cycles >= 600 else "",
            ))

        chem_code = wmi_bat.get("chemistry", 0)
        if chem_code:
            results.append(CheckResult(
                key="battery_health", label="Chemistry",
                value=_CHEMISTRY_MAP.get(chem_code, "Unknown"), status=Status.INFO,
            ))

        mfr = wmi_bat.get("manufacturer", "")
        if mfr:
            results.append(CheckResult(
                key="battery_mfr", label="Manufacturer", value=mfr, status=Status.INFO,
            ))

        voltage = wmi_bat.get("voltage", 0)
        if voltage > 0:
            results.append(CheckResult(
                key="battery_voltage", label="Voltage",
                value=fmt_voltage(voltage), status=Status.INFO,
            ))

    elif IS_MAC:
        mac_bat = _mac_battery_detail()
        if mac_bat:
            design_cap = mac_bat.get("design_capacity", 0)
            max_cap    = mac_bat.get("max_capacity", 0)

            if design_cap > 0 and max_cap > 0:
                health_pct = 100.0 * max_cap / design_cap
                wear       = 100.0 - health_pct
                h_status   = (Status.PASS if health_pct >= 80
                              else Status.WARN if health_pct >= 50
                              else Status.FAIL)
                results.append(CheckResult(
                    key="battery_health", label="Battery Health",
                    value=f"{health_pct:.1f}%", status=h_status,
                    detail="Battery has significant wear — replacement recommended" if health_pct < 60 else "",
                ))
                results.append(CheckResult(
                    key="battery_wear", label="Wear Level",
                    value=f"{wear:.1f}%", status=h_status,
                ))
                results.append(CheckResult(
                    key="battery_capacity", label="Full Capacity",
                    value=f"{max_cap} mAh", status=Status.INFO,
                ))
                results.append(CheckResult(
                    key="battery_design", label="Design Capacity",
                    value=f"{design_cap} mAh", status=Status.INFO,
                ))

            cycles = mac_bat.get("cycle_count", 0)
            if cycles:
                c_status = Status.PASS if cycles < 500 else (Status.WARN if cycles < 1000 else Status.FAIL)
                results.append(CheckResult(
                    key="battery_cycles", label="Charge Cycles",
                    value=str(cycles), status=c_status,
                    detail="Apple recommends battery service after ~1000 cycles" if cycles >= 1000 else "",
                ))

            temp_raw = mac_bat.get("temperature")
            if temp_raw:
                temp_c = temp_raw / 100.0
                if 0 < temp_c < 80:
                    t_status = Status.PASS if temp_c < 40 else (Status.WARN if temp_c < 55 else Status.FAIL)
                    results.append(CheckResult(
                        key="battery_temp", label="Battery Temperature",
                        value=f"{temp_c:.1f} °C", status=t_status,
                    ))

            mfr = mac_bat.get("manufacturer", "")
            if mfr:
                results.append(CheckResult(
                    key="battery_mfr", label="Manufacturer", value=mfr, status=Status.INFO,
                ))

            v_mv = mac_bat.get("voltage_mv", 0)
            if v_mv > 0:
                results.append(CheckResult(
                    key="battery_voltage", label="Voltage",
                    value=fmt_voltage(v_mv / 1000), status=Status.INFO,
                ))

    return results
