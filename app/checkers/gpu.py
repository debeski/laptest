import platform
from app.checkers.base import CheckResult, Status
from app.utils.formatters import fmt_bytes
from app.utils.platform_utils import IS_WINDOWS


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


def _classify(name: str) -> tuple[str, str]:
    n = name.lower()
    if any(x in n for x in ("nvidia", "geforce", "rtx", "gtx", "quadro")):
        mfr = "NVIDIA"
    elif any(x in n for x in ("amd", "radeon", "rx ")):
        mfr = "AMD"
    elif any(x in n for x in ("intel", "iris", "uhd", "hd graphics")):
        mfr = "Intel"
    else:
        mfr = "Unknown"
    gtype = "Integrated" if any(x in n for x in ("intel", "iris", "uhd", "hd graphics")) else "Dedicated"
    return mfr, gtype


def run() -> list[CheckResult]:
    results = []
    gpus    = _wmi_gpu_info()
    vrams   = _vram_from_registry()

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

        # VRAM: prefer 64-bit registry value, fall back to WMI (capped at 4 GB)
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

    return results
