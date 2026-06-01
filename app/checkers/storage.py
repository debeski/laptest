import json
import os
import tempfile
import time
import platform
import psutil
from app.checkers.base import CheckResult, Status
from app.utils.formatters import fmt_bytes, fmt_speed
from app.utils.platform_utils import run_ps, IS_WINDOWS, IS_MAC


# ── Windows backends ──────────────────────────────────────────────────────

def _all_physical_disks_win() -> list[dict]:
    if not IS_WINDOWS:
        return []
    raw = run_ps(
        "Get-PhysicalDisk | Select-Object FriendlyName,Size,MediaType,HealthStatus,BusType "
        "| ConvertTo-Json -Compress",
        timeout=15,
    )
    if not raw:
        return []
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            data = [data]
        return data
    except Exception:
        return []


def _reliability_counters_win() -> list[dict]:
    if not IS_WINDOWS:
        return []
    raw = run_ps(
        "Get-PhysicalDisk | Get-StorageReliabilityCounter "
        "| Select-Object DeviceId,PowerOnHours,Temperature,ReadErrorsTotal,WriteErrorsTotal "
        "| ConvertTo-Json -Compress",
        timeout=15,
    )
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return [data] if isinstance(data, dict) else data
    except Exception:
        return []


def _partition_styles_win() -> dict[int, str]:
    if not IS_WINDOWS:
        return {}
    raw = run_ps(
        "Get-Disk | Select-Object Number,PartitionStyle | ConvertTo-Json -Compress",
        timeout=10,
    )
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            data = [data]
        return {int(d.get("Number", -1)): d.get("PartitionStyle", "Unknown") for d in data}
    except Exception:
        return {}


# ── macOS backends ────────────────────────────────────────────────────────

def _mac_disks() -> list[dict]:
    """
    Return physical disk info on macOS via system_profiler SPStorageDataType.
    Deduplicates by physical device name so each physical drive appears once.
    """
    if not IS_MAC:
        return []
    from app.utils.platform_utils import run_sp
    data = run_sp("SPStorageDataType", timeout=15)
    seen: dict[str, dict] = {}
    for vol in data.get("SPStorageDataType", []):
        phys = vol.get("physical_drive", {})
        dev_name = phys.get("device_name", "").strip()
        if not dev_name:
            continue
        if dev_name in seen:
            continue
        seen[dev_name] = {
            "name":        dev_name,
            "medium_type": phys.get("medium_type", ""),
            "protocol":    phys.get("protocol", ""),
            "smart":       phys.get("smart_status", ""),
            "solid_state": phys.get("is_solid_state", "") == "yes",
            "size_bytes":  int(vol.get("size_in_bytes", 0)),
        }
    return list(seen.values())


# ── Shared helpers ────────────────────────────────────────────────────────

def _disk_speed_on_system_drive() -> tuple[float, float]:
    try:
        size    = 50 * 1024 * 1024
        payload = os.urandom(size)
        tmp     = tempfile.mktemp()

        t0 = time.perf_counter()
        with open(tmp, "wb") as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        write_s = time.perf_counter() - t0

        t0 = time.perf_counter()
        with open(tmp, "rb") as f:
            f.read()
        read_s = time.perf_counter() - t0

        os.unlink(tmp)
        return size / read_s / (1024 * 1024), size / write_s / (1024 * 1024)
    except Exception:
        return 0.0, 0.0


def _classify_type_win(media: str, bus: str) -> str:
    m, b = (media or "").lower(), (bus or "").lower()
    if b == "nvme" or "nvme" in m:
        return "NVMe SSD"
    if "ssd" in m or "solid" in m:
        return f"SSD ({bus})" if bus else "SSD"
    if "hdd" in m or "hard" in m or "spinning" in m:
        return f"HDD ({bus})" if bus else "HDD"
    if b == "usb":
        return "USB Drive"
    return media or "Unknown"


def _classify_type_mac(medium_type: str, protocol: str, solid_state: bool) -> str:
    m = (medium_type or "").lower()
    p = (protocol or "").lower()
    if "nvme" in p or "nvme" in m:
        return "NVMe SSD"
    if "apple fabric" in p:
        return "NVMe SSD (Apple)"
    if solid_state or "ssd" in m:
        return f"SSD ({protocol})" if protocol else "SSD"
    if "hdd" in m or "hard" in m:
        return "HDD"
    return medium_type or "SSD"


# ── Run ───────────────────────────────────────────────────────────────────

def run() -> list[CheckResult]:
    results: list[CheckResult] = []

    if IS_WINDOWS:
        disks = _all_physical_disks_win()
        rel   = _reliability_counters_win()
        parts = _partition_styles_win()

        rel_by_id = {}
        for r in rel:
            did = r.get("DeviceId")
            if did is not None:
                rel_by_id[str(did)] = r

        if not disks:
            # Fallback: psutil partitions only
            try:
                for p in psutil.disk_partitions():
                    u = psutil.disk_usage(p.mountpoint)
                    results.append(CheckResult(
                        key="storage_capacity", label=f"Drive ({p.mountpoint})",
                        value=fmt_bytes(u.total), status=Status.INFO,
                    ))
            except Exception:
                pass
            results.append(CheckResult(
                key="storage_health", label="Drive Health",
                value="Run as administrator for full SMART data", status=Status.INFO,
            ))
            return results

        for idx, disk in enumerate(disks):
            pfx    = f"Disk {idx + 1}: " if len(disks) > 1 else ""
            name   = disk.get("FriendlyName") or f"Disk {idx}"
            size_b = int(disk.get("Size") or 0)
            media  = disk.get("MediaType") or ""
            health = disk.get("HealthStatus") or "Unknown"
            bus    = disk.get("BusType") or ""
            dtype  = _classify_type_win(media, bus)

            results.append(CheckResult(
                key="storage_model", label=f"{pfx}Model",
                value=name, status=Status.INFO,
            ))
            results.append(CheckResult(
                key="storage_type", label=f"{pfx}Type",
                value=dtype,
                status=Status.PASS if "SSD" in dtype or "NVMe" in dtype
                       else (Status.WARN if "HDD" in dtype else Status.INFO),
                detail="HDDs are significantly slower than SSDs" if "HDD" in dtype else "",
            ))
            if size_b:
                results.append(CheckResult(
                    key="storage_capacity", label=f"{pfx}Capacity",
                    value=fmt_bytes(size_b), status=Status.INFO,
                ))

            h_status = (Status.PASS if health == "Healthy"
                        else Status.FAIL if health == "Unhealthy"
                        else Status.WARN)
            results.append(CheckResult(
                key="storage_health", label=f"{pfx}Health (SMART)",
                value=health, status=h_status,
            ))

            style = parts.get(idx, "Unknown")
            results.append(CheckResult(
                key="storage_partition", label=f"{pfx}Partition Style",
                value=style,
                status=Status.PASS if style == "GPT"
                       else (Status.WARN if style == "MBR" else Status.INFO),
                detail="MBR limits disk to 2 TB and 4 primary partitions" if style == "MBR" else "",
            ))

            rel_data = rel_by_id.get(str(idx))
            if rel_data:
                hours = rel_data.get("PowerOnHours")
                if hours:
                    years = int(hours) / 8760
                    age_status = Status.PASS if years < 3 else (Status.WARN if years < 5 else Status.FAIL)
                    results.append(CheckResult(
                        key="storage_age", label=f"{pfx}Power-On Hours",
                        value=f"{hours:,} h ({years:.1f} years)",
                        status=age_status,
                        detail="Drive is heavily used — consider replacement" if years >= 5 else "",
                    ))
                temp = rel_data.get("Temperature")
                if temp:
                    t_status = Status.PASS if temp < 45 else (Status.WARN if temp < 55 else Status.FAIL)
                    results.append(CheckResult(
                        key="storage_temp", label=f"{pfx}Temperature",
                        value=f"{temp} °C", status=t_status,
                    ))
                read_err  = rel_data.get("ReadErrorsTotal", 0) or 0
                write_err = rel_data.get("WriteErrorsTotal", 0) or 0
                if read_err or write_err:
                    err_status = Status.FAIL if (read_err + write_err) > 0 else Status.PASS
                    results.append(CheckResult(
                        key="storage_reallocated", label=f"{pfx}Read/Write Errors",
                        value=f"R:{read_err}  W:{write_err}", status=err_status,
                        detail="Non-zero errors indicate potential drive failure" if err_status == Status.FAIL else "",
                    ))

    elif IS_MAC:
        disks = _mac_disks()
        if not disks:
            # Fallback: psutil partitions (deduplicated to mountpoint = /)
            try:
                u = psutil.disk_usage("/")
                results.append(CheckResult(
                    key="storage_capacity", label="Drive (/)",
                    value=fmt_bytes(u.total), status=Status.INFO,
                ))
            except Exception:
                pass
            results.append(CheckResult(
                key="storage_health", label="Drive Health",
                value="Run as administrator for full storage data", status=Status.INFO,
            ))
        else:
            for idx, disk in enumerate(disks):
                pfx   = f"Disk {idx + 1}: " if len(disks) > 1 else ""
                dtype = _classify_type_mac(
                    disk["medium_type"], disk["protocol"], disk["solid_state"]
                )
                results.append(CheckResult(
                    key="storage_model", label=f"{pfx}Model",
                    value=disk["name"], status=Status.INFO,
                ))
                results.append(CheckResult(
                    key="storage_type", label=f"{pfx}Type",
                    value=dtype,
                    status=Status.PASS if "SSD" in dtype or "NVMe" in dtype
                           else (Status.WARN if "HDD" in dtype else Status.INFO),
                ))
                if disk["size_bytes"] > 0:
                    results.append(CheckResult(
                        key="storage_capacity", label=f"{pfx}Capacity",
                        value=fmt_bytes(disk["size_bytes"]), status=Status.INFO,
                    ))
                smart = disk.get("smart") or ""
                if smart:
                    smart_ok = "verified" in smart.lower() or "ok" in smart.lower()
                    results.append(CheckResult(
                        key="storage_health", label=f"{pfx}SMART Status",
                        value=smart,
                        status=Status.PASS if smart_ok else Status.WARN,
                    ))

        # macOS APFS doesn't have MBR/GPT in the traditional sense — all Apple Fabric drives use GPT
        results.append(CheckResult(
            key="storage_partition", label="Partition Style",
            value="APFS / GPT (macOS default)", status=Status.PASS,
        ))

    else:
        # Generic psutil fallback
        try:
            for p in psutil.disk_partitions():
                try:
                    u = psutil.disk_usage(p.mountpoint)
                    results.append(CheckResult(
                        key="storage_capacity", label=f"Drive ({p.mountpoint})",
                        value=fmt_bytes(u.total), status=Status.INFO,
                    ))
                except Exception:
                    pass
        except Exception:
            pass

    # Speed benchmark — always run on system drive
    sys_mount = "C:\\" if IS_WINDOWS else "/"
    try:
        u = psutil.disk_usage(sys_mount)
        results.append(CheckResult(
            key="storage_used", label="System Drive Used",
            value=f"{fmt_bytes(u.used)} of {fmt_bytes(u.total)} ({u.percent:.0f}%)",
            status=Status.WARN if u.percent > 85 else Status.PASS,
        ))
    except Exception:
        pass

    read_s, write_s = _disk_speed_on_system_drive()
    if read_s > 0:
        r_status = Status.PASS if read_s > 200 else (Status.WARN if read_s > 80 else Status.FAIL)
        results.append(CheckResult(
            key="storage_read_speed", label="System Drive Read Speed",
            value=fmt_speed(read_s), status=r_status,
        ))
    if write_s > 0:
        w_status = Status.PASS if write_s > 150 else (Status.WARN if write_s > 60 else Status.FAIL)
        results.append(CheckResult(
            key="storage_write_speed", label="System Drive Write Speed",
            value=fmt_speed(write_s), status=w_status,
        ))

    return results
