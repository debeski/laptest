import platform
from app.checkers.base import CheckResult, Status
from app.utils.formatters import fmt_bytes
from app.utils.platform_utils import IS_WINDOWS, IS_MAC


def _vram_from_registry() -> list[int]:
    """Read actual 64-bit VRAM values from the display adapter registry keys."""
    if not IS_WINDOWS:
        return []
    try:
        import winreg
        key_path = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
        vrams = []
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
            i = 0
            while True:
                try:
                    subname = winreg.EnumKey(key, i)
                    i += 1
                    if not subname.isdigit():
                        continue
                    with winreg.OpenKey(key, subname) as sub:
                        for val_name in ("HardwareInformation.qwMemorySize",
                                         "HardwareInformation.MemorySize"):
                            try:
                                v, _ = winreg.QueryValueEx(sub, val_name)
                                if v and int(v) > 0:
                                    vrams.append(int(v))
                                    break
                            except OSError:
                                continue
                except OSError:
                    break
        return vrams
    except Exception:
        return []


def _wmi_gpu_info() -> list[dict]:
    if not IS_WINDOWS:
        return []
    try:
        import wmi
        c = wmi.WMI()
        gpus = []
        for g in c.Win32_VideoController():
            gpus.append({
                "name":   (g.Name or "").strip(),
                "vram":   int(g.AdapterRAM or 0),
                "driver": (g.DriverVersion or "").strip(),
                "status": (g.Status or "").strip(),
            })
        return gpus
    except Exception:
        return []


def _mac_gpu_info() -> list[dict]:
    """Read GPU info via system_profiler SPDisplaysDataType on macOS."""
    if not IS_MAC:
        return []
    from app.utils.platform_utils import run_sp
    data = run_sp("SPDisplaysDataType", timeout=15)
    gpus = []
    for entry in data.get("SPDisplaysDataType", []):
        name   = entry.get("_name", "").strip()
        vendor = entry.get("spdisplays_vendor", "").strip()
        vram_s = entry.get("spdisplays_vram", "").strip()
        cores  = entry.get("sppci_cores", "").strip()
        bus    = entry.get("sppci_bus", "").strip()
        if not name:
            continue
        # Parse VRAM string e.g. "8 GB", "1536 MB", "Shared"
        vram_bytes = 0
        vram_label = vram_s
        try:
            parts = vram_s.lower().split()
            if len(parts) >= 2:
                val = float(parts[0])
                if "gb" in parts[1]:
                    vram_bytes = int(val * 1024 ** 3)
                elif "mb" in parts[1]:
                    vram_bytes = int(val * 1024 ** 2)
        except Exception:
            pass
        gpus.append({
            "name":       name,
            "vendor":     vendor,
            "vram_bytes": vram_bytes,
            "vram_label": vram_label,
            "cores":      cores,
            "bus":        bus,
        })
    return gpus


def _classify(name: str) -> tuple[str, str]:
    n = name.lower()
    if any(x in n for x in ("nvidia", "geforce", "rtx", "gtx", "quadro")):
        mfr = "NVIDIA"
    elif any(x in n for x in ("amd", "radeon", "rx ")):
        mfr = "AMD"
    elif any(x in n for x in ("intel", "iris", "uhd", "hd graphics")):
        mfr = "Intel"
    elif "apple" in n:
        mfr = "Apple"
    else:
        mfr = "Unknown"
    gtype = "Integrated" if any(x in n for x in ("intel", "iris", "uhd", "hd graphics", "apple")) else "Dedicated"
    return mfr, gtype


def run() -> list[CheckResult]:
    results = []

    if IS_WINDOWS:
        gpus  = _wmi_gpu_info()
        vrams = _vram_from_registry()

        if not gpus:
            results.append(CheckResult(
                key="gpu_model", label="GPU",
                value="Could not detect", status=Status.INFO,
            ))
            return results

        for i, g in enumerate(gpus):
            pfx = f"GPU {i + 1}: " if len(gpus) > 1 else ""
            name = g["name"] or "Unknown GPU"
            mfr, gtype = _classify(name)

            results.append(CheckResult(
                key="gpu_model", label=f"{pfx}Model",
                value=name, status=Status.INFO,
            ))
            results.append(CheckResult(
                key="gpu_manufacturer", label=f"{pfx}Manufacturer",
                value=mfr, status=Status.INFO,
            ))
            results.append(CheckResult(
                key="gpu_type", label=f"{pfx}Type",
                value=gtype, status=Status.INFO,
            ))

            vram = vrams[i] if i < len(vrams) else g["vram"]
            if not vram and i < len(vrams):
                vram = vrams[i]
            if vram and vram > 0:
                vram_gb = vram / (1024 ** 3)
                v_status = (Status.PASS if vram_gb >= 4
                            else Status.WARN if vram_gb >= 2
                            else Status.FAIL)
                results.append(CheckResult(
                    key="gpu_vram", label=f"{pfx}VRAM",
                    value=fmt_bytes(vram), status=v_status,
                    detail="2 GB VRAM is insufficient for modern apps" if vram_gb < 2 else "",
                ))

            if g["driver"]:
                results.append(CheckResult(
                    key="gpu_driver", label=f"{pfx}Driver",
                    value=g["driver"], status=Status.INFO,
                ))
            if g["status"]:
                results.append(CheckResult(
                    key="gpu_model", label=f"{pfx}Device Status",
                    value=g["status"],
                    status=Status.PASS if g["status"] == "OK" else Status.FAIL,
                ))

    elif IS_MAC:
        gpus = _mac_gpu_info()
        if not gpus:
            results.append(CheckResult(
                key="gpu_model", label="GPU",
                value="Could not detect", status=Status.INFO,
            ))
            return results

        for i, g in enumerate(gpus):
            pfx = f"GPU {i + 1}: " if len(gpus) > 1 else ""
            name = g["name"]
            mfr, gtype = _classify(name)

            results.append(CheckResult(
                key="gpu_model", label=f"{pfx}Model",
                value=name, status=Status.INFO,
            ))
            if g["vendor"]:
                results.append(CheckResult(
                    key="gpu_manufacturer", label=f"{pfx}Vendor",
                    value=g["vendor"], status=Status.INFO,
                ))
            results.append(CheckResult(
                key="gpu_type", label=f"{pfx}Type",
                value=gtype, status=Status.INFO,
            ))
            if g["cores"]:
                results.append(CheckResult(
                    key="gpu_cores", label=f"{pfx}GPU Cores",
                    value=g["cores"], status=Status.INFO,
                ))
            if g["vram_bytes"] > 0:
                vram_gb = g["vram_bytes"] / (1024 ** 3)
                v_status = (Status.PASS if vram_gb >= 4
                            else Status.WARN if vram_gb >= 2
                            else Status.FAIL)
                results.append(CheckResult(
                    key="gpu_vram", label=f"{pfx}VRAM",
                    value=fmt_bytes(g["vram_bytes"]), status=v_status,
                ))
            elif g["vram_label"]:
                results.append(CheckResult(
                    key="gpu_vram", label=f"{pfx}VRAM",
                    value=g["vram_label"], status=Status.INFO,
                ))
    else:
        results.append(CheckResult(
            key="gpu_model", label="GPU",
            value="Could not detect", status=Status.INFO,
        ))

    return results
