import platform
import psutil
from app.checkers.base import CheckResult, Status
from app.utils.formatters import fmt_temp, fmt_rpm
from app.utils.platform_utils import run_ps, IS_WINDOWS


def _cpu_temp_from_wmi() -> float | None:
    """Read CPU temp via WMI thermal zone (Kelvin → Celsius)."""
    try:
        import wmi
        c = wmi.WMI(namespace="root/wmi")
        temps = []
        for t in c.MSAcpi_ThermalZoneTemperature():
            celsius = t.CurrentTemperature / 10.0 - 273.15
            if 10 < celsius < 120:
                temps.append(celsius)
        if temps:
            return max(temps)
    except Exception:
        pass
    return None


def _cpu_temp_from_ps() -> float | None:
    """Read CPU temp via PowerShell Get-WmiObject thermal zone."""
    try:
        out = run_ps(
            "(Get-WmiObject -Namespace root/wmi -Class MSAcpi_ThermalZoneTemperature"
            " | Select-Object -ExpandProperty CurrentTemperature | Measure-Object -Maximum).Maximum",
            timeout=8,
        )
        v = float(out.strip())
        celsius = v / 10.0 - 273.15
        if 10 < celsius < 120:
            return celsius
    except Exception:
        pass
    return None


def _all_temps() -> dict[str, float]:
    temps: dict[str, float] = {}
    try:
        for label, entries in (psutil.sensors_temperatures() or {}).items():
            for e in entries:
                key = f"{label}/{e.label}" if e.label else label
                temps[key] = e.current
    except Exception:
        pass

    if not temps:
        t = _cpu_temp_from_wmi() or _cpu_temp_from_ps()
        if t is not None:
            temps["cpu"] = t
    return temps


def _fans() -> list[dict]:
    fans = []
    try:
        for label, entries in (psutil.sensors_fans() or {}).items():
            for e in entries:
                fans.append({"label": e.label or label, "rpm": e.current})
    except Exception:
        pass
    if not fans and IS_WINDOWS:
        try:
            import wmi
            c = wmi.WMI()
            for f in c.Win32_Fan():
                fans.append({"label": (f.Name or "Fan").strip(), "rpm": int(f.DesiredSpeed or 0)})
        except Exception:
            pass
    return fans


def _throttle_status() -> tuple[str, Status]:
    """Estimate throttling by comparing current vs max CPU frequency."""
    try:
        freq = psutil.cpu_freq()
        if freq and freq.max > 0:
            ratio = freq.current / freq.max
            if ratio < 0.5:
                return f"Likely (running at {ratio * 100:.0f}% of max)", Status.WARN
            return "Not detected", Status.PASS
    except Exception:
        pass
    return "Unknown", Status.INFO


def run() -> list[CheckResult]:
    results = []
    temps = _all_temps()

    if temps:
        cpu_keys = [k for k in temps if any(
            x in k.lower() for x in ("core", "cpu", "package", "k10", "coretemp")
        )]
        cpu_temp = max(temps[k] for k in cpu_keys) if cpu_keys else (
            temps.get("cpu") or next(iter(temps.values()), None)
        )
        if cpu_temp is not None:
            t_status = (Status.PASS if cpu_temp < 70
                        else Status.WARN if cpu_temp < 90
                        else Status.FAIL)
            results.append(CheckResult(
                key="thermal_cpu_temp", label="CPU Temperature",
                value=fmt_temp(cpu_temp), status=t_status,
                detail="Very hot — check thermal paste and fan clearance" if cpu_temp >= 90 else "",
            ))

        gpu_keys = [k for k in temps if "gpu" in k.lower()]
        if gpu_keys:
            gpu_temp = max(temps[k] for k in gpu_keys)
            g_status = (Status.PASS if gpu_temp < 80
                        else Status.WARN if gpu_temp < 95
                        else Status.FAIL)
            results.append(CheckResult(
                key="thermal_gpu_temp", label="GPU Temperature",
                value=fmt_temp(gpu_temp), status=g_status,
            ))
    else:
        results.append(CheckResult(
            key="thermal_cpu_temp", label="Temperature Sensors",
            value="Not accessible",
            status=Status.INFO,
            detail="Temperature monitoring requires elevated permissions "
                   "or hardware-specific drivers (try running as administrator)",
        ))

    fans = _fans()
    if fans:
        results.append(CheckResult(
            key="thermal_fan_count", label="Fan Count",
            value=str(len(fans)), status=Status.INFO,
        ))
        for f in fans:
            rpm = f["rpm"]
            f_status = (Status.PASS if rpm > 500
                        else Status.WARN if rpm > 0
                        else Status.FAIL)
            results.append(CheckResult(
                key="thermal_fan_speed", label=f"Fan: {f['label']}",
                value=fmt_rpm(rpm) if rpm > 0 else "0 RPM — stalled?",
                status=f_status,
                detail="Fan may be stalled — check physically" if rpm == 0 else "",
            ))
    else:
        results.append(CheckResult(
            key="thermal_fan_count", label="Fan Data",
            value="Not accessible via OS",
            status=Status.INFO,
            detail="Fan RPM data typically requires vendor WMI extensions "
                   "(Dell, HP, Lenovo) or tools like HWInfo",
        ))

    throttle, t_status = _throttle_status()
    results.append(CheckResult(
        key="thermal_throttle", label="Thermal Throttling",
        value=throttle, status=t_status,
        detail="CPU is throttling — clean vents, check thermal paste" if t_status == Status.WARN else "",
    ))

    return results
