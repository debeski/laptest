import platform
import psutil
from app.checkers.base import CheckResult, Status
from app.utils.formatters import fmt_bytes, fmt_mhz, fmt_voltage, fmt_pct

_RAM_TYPES = {
    0: "Unknown", 1: "Other", 2: "DRAM", 20: "DDR",
    21: "DDR2", 24: "DDR3", 26: "DDR4", 34: "DDR5",
}


def _wmi_ram_info() -> tuple[list[dict], int]:
    """Returns (module_list, total_slots)."""
    if platform.system() != "Windows":
        return [], 0
    try:
        import wmi
        c = wmi.WMI()
        total_slots = 0
        try:
            for arr in c.Win32_PhysicalMemoryArray():
                total_slots = max(total_slots, int(arr.MemoryDevices or 0))
        except Exception:
            pass
        modules = []
        for m in c.Win32_PhysicalMemory():
            modules.append({
                "capacity":     int(m.Capacity or 0),
                "speed":        int(m.Speed or 0),
                "type":         _RAM_TYPES.get(int(m.MemoryType or 0), "Unknown"),
                "voltage":      int(m.ConfiguredVoltage or 0) / 1000,
                "manufacturer": (m.Manufacturer or "").strip(),
                "part_number":  (m.PartNumber or "").strip(),
                "slot":         (m.DeviceLocator or "").strip(),
            })
        return modules, total_slots
    except Exception:
        return [], 0


def run() -> list[CheckResult]:
    results = []
    vm = psutil.virtual_memory()
    total_gb = vm.total / (1024 ** 3)

    total_status = (Status.FAIL if total_gb < 4
                    else Status.WARN if total_gb < 8
                    else Status.PASS)
    results.append(CheckResult(
        key="memory_total", label="Total RAM",
        value=fmt_bytes(vm.total), status=total_status,
        detail=("4 GB is insufficient for modern use" if total_gb < 4
                else "8 GB may be limiting for multitasking" if total_gb < 8 else ""),
    ))
    results.append(CheckResult(
        key="memory_used", label="Used",
        value=f"{fmt_bytes(vm.used)} ({vm.percent:.0f}%)",
        status=Status.WARN if vm.percent > 80 else Status.PASS,
    ))
    results.append(CheckResult(
        key="memory_available", label="Available",
        value=fmt_bytes(vm.available),
        status=Status.WARN if vm.available < 1 * 1024 ** 3 else Status.PASS,
    ))

    modules, total_slots = _wmi_ram_info()
    if modules:
        types  = list({m["type"] for m in modules if m["type"] not in ("Unknown", "Other")})
        speeds = [m["speed"] for m in modules if m["speed"] > 0]
        used   = len(modules)
        dual   = used >= 2

        if types:
            results.append(CheckResult(
                key="memory_type", label="RAM Type",
                value=", ".join(types), status=Status.INFO,
            ))
        if speeds:
            spd = max(speeds)
            spd_status = (Status.PASS if spd >= 2400
                          else Status.WARN if spd >= 1600
                          else Status.FAIL)
            results.append(CheckResult(
                key="memory_speed", label="Speed",
                value=fmt_mhz(spd), status=spd_status,
                detail="Very slow by modern standards" if spd < 2000 else "",
            ))

        slot_label = (f"{used} of {total_slots}" if total_slots > used
                      else f"{used}" + (f" of {total_slots}" if total_slots else ""))
        results.append(CheckResult(
            key="memory_slots", label="Slots Used",
            value=slot_label, status=Status.INFO,
        ))
        results.append(CheckResult(
            key="memory_channels", label="Channel Mode",
            value="Dual-channel" if dual else "Single-channel",
            status=Status.PASS if dual else Status.WARN,
            detail="Single-channel halves memory bandwidth" if not dual else "",
        ))

        voltages = [m["voltage"] for m in modules if m["voltage"] > 0]
        if voltages:
            results.append(CheckResult(
                key="memory_voltage", label="Voltage",
                value=fmt_voltage(voltages[0]), status=Status.INFO,
            ))

        # Per-module detail
        for m in modules:
            label = m["slot"] or f"Module {modules.index(m) + 1}"
            parts = [p for p in [m["manufacturer"], m["part_number"], fmt_bytes(m["capacity"]) if m["capacity"] else ""] if p]
            if parts:
                results.append(CheckResult(
                    key="memory_type", label=label,
                    value=" · ".join(parts), status=Status.INFO,
                ))
    else:
        results.append(CheckResult(
            key="memory_type", label="Module Detail",
            value="Requires elevated permissions for WMI access",
            status=Status.INFO,
        ))

    return results
