import platform
import psutil
from app.checkers.base import CheckResult, Status
from app.utils.formatters import fmt_mhz, fmt_temp, fmt_pct
from app.utils.platform_utils import IS_WINDOWS, IS_MAC


def _wmi_cpu() -> dict:
    if not IS_WINDOWS:
        return {}
    try:
        import wmi
        c = wmi.WMI()
        for cpu in c.Win32_Processor():
            return {
                "name":         (cpu.Name or "").strip(),
                "manufacturer": (cpu.Manufacturer or "").strip(),
                "cores":        int(cpu.NumberOfCores or 0),
                "threads":      int(getattr(cpu, "ThreadCount", 0) or
                                    getattr(cpu, "NumberOfLogicalProcessors", 0) or 0),
                "max_speed":    int(cpu.MaxClockSpeed or 0),
                "current":      int(cpu.CurrentClockSpeed or 0),
                "l2_kb":        int(cpu.L2CacheSize or 0),
                "l3_kb":        int(cpu.L3CacheSize or 0),
            }
    except Exception:
        return {}


def _mac_cpu_name() -> str:
    """Get CPU/chip name on macOS (works for both Intel and Apple Silicon)."""
    from app.utils.platform_utils import run_command, run_sp
    # Intel: sysctl returns the brand string directly
    name = run_command(["sysctl", "-n", "machdep.cpu.brand_string"], timeout=5)
    if name:
        return name
    # Apple Silicon: use system_profiler
    data = run_sp("SPHardwareDataType", timeout=10)
    for hw in data.get("SPHardwareDataType", []):
        chip = hw.get("cpu_type", "")
        if chip:
            return chip
    return ""


def _cpu_generation(brand: str) -> str:
    import re
    b = brand.lower()
    if "intel" in b:
        m = re.search(r"i[3579]-(\d{4,5})", b)
        if m:
            n = int(m.group(1))
            gen = n // 1000 if n >= 10000 else n // 100
            return f"{gen}th Gen Intel"
        if "core ultra" in b:
            return "Intel Core Ultra (Gen 2)"
    if "amd" in b or "ryzen" in b:
        m = re.search(r"ryzen\s+[39]\s+(\d{4})", b)
        if m:
            return f"AMD Ryzen Gen {int(m.group(1)) // 1000}"
    return ""


def _cpu_temp() -> float | None:
    if IS_WINDOWS:
        try:
            import wmi
            c = wmi.WMI(namespace="root/wmi")
            vals = []
            for t in c.MSAcpi_ThermalZoneTemperature():
                celsius = t.CurrentTemperature / 10.0 - 273.15
                if 10 < celsius < 120:
                    vals.append(celsius)
            if vals:
                return max(vals)
        except Exception:
            pass
    try:
        sensors = psutil.sensors_temperatures()
        for key in ("coretemp", "k10temp", "cpu_thermal", "acpitz"):
            if key in sensors and sensors[key]:
                return sensors[key][0].current
    except Exception:
        pass
    return None


def run() -> list[CheckResult]:
    results = []
    info = _wmi_cpu()

    if IS_MAC:
        name = _mac_cpu_name() or platform.processor() or "Unknown"
    else:
        name = info.get("name") or platform.processor() or "Unknown"
    results.append(CheckResult(
        key="cpu_model", label="CPU Model",
        value=name, status=Status.INFO,
    ))

    mfr = info.get("manufacturer") or ""
    if not mfr:
        if "intel" in name.lower():
            mfr = "Intel"
        elif "amd" in name.lower():
            mfr = "AMD"
    if mfr:
        results.append(CheckResult(
            key="cpu_manufacturer", label="Manufacturer",
            value=mfr, status=Status.INFO,
        ))

    results.append(CheckResult(
        key="cpu_arch", label="Architecture",
        value=platform.machine(), status=Status.INFO,
    ))

    gen = _cpu_generation(name)
    if gen:
        results.append(CheckResult(
            key="cpu_generation", label="Generation",
            value=gen, status=Status.INFO,
        ))

    phys    = info.get("cores")    or psutil.cpu_count(logical=False) or 1
    logical = info.get("threads")  or psutil.cpu_count(logical=True)  or 1
    results.append(CheckResult(
        key="cpu_cores", label="Cores / Threads",
        value=f"{phys} / {logical}",
        status=Status.WARN if phys < 2 else Status.PASS,
        detail="Dual-core is very limited for modern use" if phys < 3 else "",
    ))

    max_mhz = info.get("max_speed", 0)
    cur_mhz = info.get("current", 0)
    if not max_mhz:
        freq = psutil.cpu_freq()
        if freq:
            max_mhz = freq.max or freq.current
            cur_mhz = freq.current

    if max_mhz:
        results.append(CheckResult(
            key="cpu_speed", label="Base / Max Speed",
            value=f"{fmt_mhz(cur_mhz)} / {fmt_mhz(max_mhz)}" if cur_mhz else fmt_mhz(max_mhz),
            status=Status.PASS if max_mhz >= 2800 else Status.WARN,
        ))

    usage = psutil.cpu_percent(interval=0.5)
    results.append(CheckResult(
        key="cpu_usage", label="Current Usage",
        value=fmt_pct(usage),
        status=Status.WARN if usage > 80 else Status.PASS,
    ))

    l3 = info.get("l3_kb", 0)
    l2 = info.get("l2_kb", 0)
    if l3:
        results.append(CheckResult(
            key="cpu_cache", label="L3 Cache",
            value=f"{l3 // 1024} MB", status=Status.INFO,
        ))
    elif l2:
        results.append(CheckResult(
            key="cpu_cache", label="L2 Cache",
            value=f"{l2} KB", status=Status.INFO,
        ))

    temp = _cpu_temp()
    if temp is not None:
        t_status = Status.PASS if temp < 70 else (Status.WARN if temp < 90 else Status.FAIL)
        results.append(CheckResult(
            key="cpu_temp", label="Temperature",
            value=fmt_temp(temp), status=t_status,
            detail="CPU is running very hot" if temp >= 90 else "",
        ))

    return results
