import platform
import psutil
from app.checkers.base import CheckResult, Status
from app.utils.formatters import fmt_duration, fmt_voltage


def _wmi_battery() -> dict:
    if platform.system() != "Windows":
        return {}
    try:
        import wmi
        c = wmi.WMI()
        for b in c.Win32_Battery():
            return {
                "name":           (b.Name or "").strip(),
                "manufacturer":   (b.Manufacturer or "").strip(),
                "design_capacity": int(b.DesignCapacity or 0),
                "full_capacity":  int(b.FullChargeCapacity or 0),
                "status":         int(b.BatteryStatus or 0),
                "chemistry":      int(b.Chemistry or 0),
                "voltage":        int(b.DesignVoltage or 0) / 1000,
            }
    except Exception:
        pass
    return {}


def _wmi_battery_static() -> dict:
    if platform.system() != "Windows":
        return {}
    try:
        import wmi
        c = wmi.WMI(namespace="root/wmi")
        for b in c.BatteryStaticData():
            return {
                "cycle_count":    int(b.CycleCount or 0),
                "design_capacity": int(b.DesignedCapacity or 0),
            }
    except Exception:
        pass
    return {}


def _wmi_battery_full_cap() -> int:
    if platform.system() != "Windows":
        return 0
    try:
        import wmi
        c = wmi.WMI(namespace="root/wmi")
        for b in c.BatteryFullChargedCapacity():
            return int(b.FullChargedCapacity or 0)
    except Exception:
        pass
    return 0


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

    charge = bat.percent
    plugged = bat.power_plugged
    secs_left = bat.secsleft

    results.append(CheckResult(
        key="battery_status",
        label="Status",
        value=("Plugged in" if plugged else "On battery"),
        status=Status.INFO,
    ))
    results.append(CheckResult(
        key="battery_health",
        label="Charge Level",
        value=f"{charge:.0f}%",
        status=Status.PASS if charge > 20 else (Status.WARN if charge > 10 else Status.FAIL),
    ))

    if secs_left and secs_left > 0:
        results.append(CheckResult(
            key="battery_time",
            label="Time Remaining",
            value=fmt_duration(secs_left),
            status=Status.PASS if secs_left > 3600 else (Status.WARN if secs_left > 1800 else Status.FAIL),
        ))

    wmi_bat = _wmi_battery()
    static = _wmi_battery_static()
    full_cap = _wmi_battery_full_cap()

    design_cap = (
        wmi_bat.get("design_capacity") or
        static.get("design_capacity") or 0
    )
    full_cap = full_cap or wmi_bat.get("full_capacity") or 0

    if design_cap > 0 and full_cap > 0:
        wear = 100.0 * (1 - full_cap / design_cap)
        health_pct = 100.0 * full_cap / design_cap
        h_status = (
            Status.PASS if health_pct >= 80
            else Status.WARN if health_pct >= 50
            else Status.FAIL
        )
        results.append(CheckResult(
            key="battery_health",
            label="Battery Health",
            value=f"{health_pct:.1f}%",
            status=h_status,
            detail="Battery has significant wear — replacement recommended" if health_pct < 60 else "",
        ))
        results.append(CheckResult(
            key="battery_wear",
            label="Wear Level",
            value=f"{wear:.1f}%",
            status=h_status,
        ))
        results.append(CheckResult(
            key="battery_capacity",
            label="Full Capacity",
            value=f"{full_cap} mWh",
            status=Status.INFO,
        ))
        results.append(CheckResult(
            key="battery_design",
            label="Design Capacity",
            value=f"{design_cap} mWh",
            status=Status.INFO,
        ))

    cycles = static.get("cycle_count", 0)
    if cycles:
        c_status = Status.PASS if cycles < 300 else (Status.WARN if cycles < 600 else Status.FAIL)
        results.append(CheckResult(
            key="battery_cycles",
            label="Charge Cycles",
            value=str(cycles),
            status=c_status,
            detail="High cycle count indicates significant battery age" if cycles >= 600 else "",
        ))

    chem_code = wmi_bat.get("chemistry", 0)
    if chem_code:
        results.append(CheckResult(
            key="battery_health",
            label="Chemistry",
            value=_CHEMISTRY_MAP.get(chem_code, "Unknown"),
            status=Status.INFO,
        ))

    mfr = wmi_bat.get("manufacturer", "")
    if mfr:
        results.append(CheckResult(
            key="battery_mfr", label="Manufacturer", value=mfr, status=Status.INFO,
        ))

    voltage = wmi_bat.get("voltage", 0)
    if voltage > 0:
        results.append(CheckResult(
            key="battery_voltage", label="Voltage", value=fmt_voltage(voltage), status=Status.INFO,
        ))

    return results
