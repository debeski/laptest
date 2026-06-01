import platform
import time
import psutil
from app.checkers.base import CheckResult, Status
from app.utils.formatters import fmt_duration
from app.utils.platform_utils import run_ps, reg_read, IS_WINDOWS


def _bios_info() -> dict:
    if not IS_WINDOWS:
        return {}
    try:
        import wmi
        c = wmi.WMI()
        for b in c.Win32_BIOS():
            return {
                "vendor":  (b.Manufacturer or "").strip(),
                "version": (b.SMBIOSBIOSVersion or b.Version or "").strip(),
                "date":    (b.ReleaseDate or "")[:8] if b.ReleaseDate else "",
            }
    except Exception:
        pass
    return {}


def _boot_mode() -> tuple[str, Status]:
    if IS_WINDOWS:
        fw = reg_read(
            r"HKLM\SYSTEM\CurrentControlSet\Control",
            "PEFirmwareType",
        )
        if fw == "2":
            return "UEFI", Status.PASS
        if fw == "1":
            return "Legacy BIOS (MBR)", Status.WARN
        # Try bcdedit
        out = run_ps("(bcdedit /enum '{current}') -join ' '", timeout=8)
        if "EFI" in out or r"\EFI\\" in out:
            return "UEFI", Status.PASS
        if out:
            return "Legacy BIOS", Status.WARN
    return "Unknown", Status.INFO


def _secure_boot() -> tuple[str, Status]:
    if IS_WINDOWS:
        out = run_ps("Confirm-SecureBootUEFI 2>$null", timeout=8).lower()
        if out == "true":
            return "Enabled", Status.PASS
        if out == "false":
            return "Disabled", Status.WARN
    return "Unknown", Status.INFO


def _tpm_info() -> tuple[str, Status]:
    if IS_WINDOWS:
        # Try Get-Tpm first
        out = run_ps(
            "try { $t=Get-Tpm; "
            "'Present:' + $t.TpmPresent + ' Ready:' + $t.TpmReady + ' Ver:' + $t.ManufacturerVersion "
            "} catch { 'error' }",
            timeout=10,
        )
        if "Present:True" in out:
            ver = ""
            for part in out.split():
                if part.startswith("Ver:"):
                    ver = part[4:]
            ready = "Ready:True" in out
            label = f"TPM {ver}".strip() if ver else "Present"
            return label, Status.PASS if ready else Status.WARN

        # TPM may be present but disabled in BIOS — check via PnP device
        pnp_out = run_ps(
            "Get-PnpDevice | Where-Object {$_.FriendlyName -match 'TPM|Trusted Platform'} "
            "| Select-Object -First 1 -ExpandProperty FriendlyName",
            timeout=10,
        )
        if pnp_out.strip():
            return f"Present (disabled in BIOS): {pnp_out.strip()}", Status.WARN

        # Check service existence
        svc = reg_read(
            r"HKLM\SYSTEM\CurrentControlSet\Services\TPM",
            "Start",
        )
        if svc is not None:
            return "Present (service found, may be disabled)", Status.WARN

    return "Not detected", Status.INFO


def _windows_activation() -> tuple[str, Status]:
    if not IS_WINDOWS:
        return "N/A", Status.INFO
    try:
        import wmi
        c = wmi.WMI()
        for prod in c.SoftwareLicensingProduct():
            name = getattr(prod, "Name", "") or ""
            status_code = getattr(prod, "LicenseStatus", None)
            if "Windows" in name and status_code == 1:
                return "Activated", Status.PASS
        return "Not activated", Status.WARN
    except Exception:
        pass
    # Fallback via slmgr output
    out = run_ps(
        "(Get-WmiObject -Class SoftwareLicensingProduct "
        "| Where-Object {$_.Name -like 'Windows*' -and $_.LicenseStatus -eq 1} "
        "| Measure-Object).Count",
        timeout=12,
    )
    try:
        if int(out.strip()) > 0:
            return "Activated", Status.PASS
    except Exception:
        pass
    return "Unknown", Status.INFO


def _als_detect() -> tuple[bool, str]:
    if IS_WINDOWS:
        out = run_ps(
            "Get-PnpDevice | Where-Object {$_.FriendlyName -match 'Light Sensor|ALS|Ambient'} "
            "| Select-Object -First 1 -ExpandProperty FriendlyName",
            timeout=10,
        )
        if out.strip():
            return True, out.strip()
    return False, "Not detected"


def run() -> list[CheckResult]:
    results = []

    results.append(CheckResult(
        key="system_os", label="Operating System",
        value=f"{platform.system()} {platform.release()} ({platform.version()[:25]})",
        status=Status.INFO,
    ))
    results.append(CheckResult(
        key="system_architecture", label="Architecture",
        value=platform.machine(), status=Status.INFO,
    ))
    results.append(CheckResult(
        key="system_hostname", label="Hostname",
        value=platform.node(), status=Status.INFO,
    ))

    uptime = time.time() - psutil.boot_time()
    results.append(CheckResult(
        key="system_uptime", label="Uptime",
        value=fmt_duration(uptime), status=Status.INFO,
    ))

    bios = _bios_info()
    if bios:
        results.append(CheckResult(
            key="system_bios_vendor", label="BIOS Vendor",
            value=bios.get("vendor") or "Unknown", status=Status.INFO,
        ))
        results.append(CheckResult(
            key="system_bios_ver", label="BIOS Version",
            value=bios.get("version") or "Unknown", status=Status.INFO,
        ))
        d = bios.get("date", "")
        if len(d) == 8:
            results.append(CheckResult(
                key="system_bios_date", label="BIOS Date",
                value=f"{d[:4]}-{d[4:6]}-{d[6:8]}", status=Status.INFO,
            ))

    boot_mode, bm_status = _boot_mode()
    results.append(CheckResult(
        key="system_boot_mode", label="Boot Mode",
        value=boot_mode, status=bm_status,
        detail="Legacy BIOS limits security and boot options" if bm_status == Status.WARN else "",
    ))

    sec_boot, sb_status = _secure_boot()
    results.append(CheckResult(
        key="system_secure_boot", label="Secure Boot",
        value=sec_boot, status=sb_status,
    ))

    tpm, tpm_status = _tpm_info()
    results.append(CheckResult(
        key="system_tpm", label="TPM",
        value=tpm, status=tpm_status,
        detail="TPM may be present but disabled in BIOS" if tpm_status == Status.WARN else "",
    ))

    activation, act_status = _windows_activation()
    results.append(CheckResult(
        key="system_activation", label="Windows Activation",
        value=activation, status=act_status,
        detail="Unactivated Windows has restricted features" if act_status == Status.WARN else "",
    ))

    als_found, als_name = _als_detect()
    results.append(CheckResult(
        key="system_als", label="Ambient Light Sensor",
        value=als_name if als_found else "Not present",
        status=Status.INFO,
    ))

    return results
