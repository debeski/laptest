def fmt_bytes(n: int | float, decimals: int = 1) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024:
            return f"{n:.{decimals}f} {unit}"
        n /= 1024
    return f"{n:.{decimals}f} PB"


def fmt_gb(n: int | float, decimals: int = 1) -> str:
    return f"{n / (1024 ** 3):.{decimals}f} GB"


def fmt_mhz(n: int | float) -> str:
    if n >= 1000:
        return f"{n / 1000:.2f} GHz"
    return f"{n:.0f} MHz"


def fmt_temp(c: float) -> str:
    return f"{c:.0f} °C"


def fmt_pct(n: float, decimals: int = 1) -> str:
    return f"{n:.{decimals}f}%"


def fmt_duration(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h:
        return f"{h}h {m}m"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


def fmt_speed(mbs: float) -> str:
    if mbs >= 1000:
        return f"{mbs / 1000:.2f} GB/s"
    return f"{mbs:.1f} MB/s"


def fmt_voltage(v: float) -> str:
    return f"{v:.3f} V"


def fmt_rpm(r: int) -> str:
    return f"{r:,} RPM"


def status_color_name(status: str) -> str:
    return {
        "pass": "status_pass",
        "warn": "status_warn",
        "fail": "status_fail",
        "info": "status_info",
    }.get(status, "text_secondary")
