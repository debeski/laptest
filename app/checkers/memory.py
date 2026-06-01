import platform
import psutil
from app.checkers.base import CheckResult, Status
from app.utils.formatters import fmt_bytes, fmt_mhz, fmt_voltage, fmt_pct
from app.utils.platform_utils import IS_WINDOWS, IS_MAC

_RAM_TYPES = {
    0: "Unknown", 1: "Other", 2: "DRAM", 20: "DDR",
    21: "DDR2", 24: "DDR3", 26: "DDR4", 34: "DDR5",
}


def _wmi_ram_info() -> tuple[list[dict], int]:
    """Returns (module_list, total_slots)."""
    if not IS_WINDOWS:
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


def _mac_ram_info() -> tuple[list[dict], int]:
    """
    Returns (module_list, total_slots) via system_profiler SPMemoryDataType.
    On Apple Silicon the memory is unified/soldered; individual slot info may
    not be available — we still report type and speed if the profiler exposes them.
    """
    if not IS_MAC:
        return [], 0
    from app.utils.platform_utils import run_sp
    data = run_sp("SPMemoryDataType", timeout=15)
    modules = []
    for entry in data.get("SPMemoryDataType", []):
        items = entry.get("_items", [])
        if items:
            # Intel Mac with actual DIMM slots
            for item in items:
                size_s   = item.get("dimm_size", "")
                ram_type = item.get("dimm_type", "")
                speed_s  = item.get("dimm_speed", "")
                status   = item.get("dimm_status", "")
                mfr      = item.get("dimm_manufacturer", "")
                slot     = item.get("_name", "")
                if "empty" in size_s.lower() or status.lower() == "empty":
                    continue
                cap = _parse_size_str(size_s)
                spd = _parse_speed_str(speed_s)
                modules.append({
                    "capacity":     cap,
                    "speed":        spd,
                    "type":         ram_type,
                    "voltage":      0.0,
                    "manufacturer": mfr,
                    "part_number":  "",
                    "slot":         slot,
                })
        else:
            # Apple Silicon: single unified memory block
            size_s   = entry.get("dimm_size", "")
            ram_type = entry.get("dimm_type", "")
            speed_s  = entry.get("dimm_speed", "")
            if size_s or ram_type:
                cap = _parse_size_str(size_s)
                spd = _parse_speed_str(speed_s)
                modules.append({
                    "capacity":     cap,
                    "speed":        spd,
                    "type":         ram_type or "Unified Memory",
                    "voltage":      0.0,
                    "manufacturer": "Apple",
                    "part_number":  "",
                    "slot":         "Unified Memory",
                })
    total_slots = len(modules)  # soldered = no free slots
    return modules, total_slots


def _parse_size_str(s: str) -> int:
    """'8 GB' → bytes, '512 MB' → bytes."""
    try:
        parts = s.strip().split()
        val = float(parts[0])
        unit = parts[1].upper() if len(parts) > 1 else "GB"
        if "GB" in unit:
            return int(val * 1024 ** 3)
        if "MB" in unit:
            return int(val * 1024 ** 2)
        if "TB" in unit:
            return int(val * 1024 ** 4)
    except Exception:
        pass
    return 0


def _parse_speed_str(s: str) -> int:
    """'2667 MHz' or '6400 MHz' → int MHz."""
    try:
        parts = s.strip().split()
        return int(float(parts[0]))
    except Exception:
        return 0


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

    if IS_WINDOWS:
        modules, total_slots = _wmi_ram_info()
    elif IS_MAC:
        modules, total_slots = _mac_ram_info()
    else:
        modules, total_slots = [], 0

    if modules:
        types  = list({m["type"] for m in modules if m["type"] not in ("Unknown", "Other", "")})
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

        # On Apple Silicon, memory is soldered — show total, skip "slots" framing
        is_unified = any(m.get("slot") == "Unified Memory" for m in modules)
        if is_unified:
            results.append(CheckResult(
                key="memory_slots", label="Memory",
                value="Unified (soldered on logic board)", status=Status.INFO,
            ))
        else:
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

        if not is_unified:
            voltages = [m["voltage"] for m in modules if m["voltage"] > 0]
            if voltages:
                results.append(CheckResult(
                    key="memory_voltage", label="Voltage",
                    value=fmt_voltage(voltages[0]), status=Status.INFO,
                ))

        for m in modules:
            if m.get("slot") == "Unified Memory":
                continue  # already shown as "Memory" row above
            label = m["slot"] or f"Module {modules.index(m) + 1}"
            parts = [p for p in [m["manufacturer"], m["part_number"],
                                  fmt_bytes(m["capacity"]) if m["capacity"] else ""] if p]
            if parts:
                results.append(CheckResult(
                    key="memory_type", label=label,
                    value=" · ".join(parts), status=Status.INFO,
                ))
    else:
        msg = ("Requires elevated permissions for WMI access" if IS_WINDOWS
               else "Module detail unavailable")
        results.append(CheckResult(
            key="memory_type", label="Module Detail",
            value=msg,
            status=Status.INFO,
        ))

    return results
