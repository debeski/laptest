import platform
import time
import psutil
from app.checkers.base import CheckResult, Status
from app.utils.formatters import fmt_duration
from app.utils.platform_utils import run_ps, reg_read, IS_WINDOWS, IS_MAC


# ── Windows backends ──────────────────────────────────────────────────────

def _bios_info_win() -> dict:
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


def _boot_mode_win() -> tuple[str, Status]:
    fw = reg_read(r"HKLM\SYSTEM\CurrentControlSet\Control", "PEFirmwareType")
    if fw == "2":
        return "UEFI", Status.PASS
    if fw == "1":
        return "Legacy BIOS (MBR)", Status.WARN
    out = run_ps("(bcdedit /enum '{current}') -join ' '", timeout=8)
    if "EFI" in out or r"\EFI\\" in out:
        return "UEFI", Status.PASS
    if out:
        return "Legacy BIOS", Status.WARN
    return "Unknown", Status.INFO


def _secure_boot_win() -> tuple[str, Status]:
    out = run_ps("Confirm-SecureBootUEFI 2>$null", timeout=8).lower()
    if out == "true":
        return "Enabled", Status.PASS
    if out == "false":
        return "Disabled", Status.WARN
    return "Unknown", Status.INFO


def _tpm_info_win() -> tuple[str, Status]:
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

    pnp_out = run_ps(
        "Get-PnpDevice | Where-Object {$_.FriendlyName -match 'TPM|Trusted Platform'} "
        "| Select-Object -First 1 -ExpandProperty FriendlyName",
        timeout=10,
    )
    if pnp_out.strip():
        return f"Present (disabled in BIOS): {pnp_out.strip()}", Status.WARN

    svc = reg_read(r"HKLM\SYSTEM\CurrentControlSet\Services\TPM", "Start")
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


def _als_detect_win() -> tuple[bool, str]:
    out = run_ps(
        "Get-PnpDevice | Where-Object {$_.FriendlyName -match 'Light Sensor|ALS|Ambient'} "
        "| Select-Object -First 1 -ExpandProperty FriendlyName",
        timeout=10,
    )
    if out.strip():
        return True, out.strip()
    return False, "Not detected"


# ── macOS backends ────────────────────────────────────────────────────────

def _mac_firmware_info() -> dict:
    """Read hardware/firmware overview from system_profiler SPHardwareDataType."""
    from app.utils.platform_utils import run_sp
    data = run_sp("SPHardwareDataType", timeout=15)
    for hw in data.get("SPHardwareDataType", []):
        return {
            "model":     hw.get("machine_name", ""),
            "model_id":  hw.get("machine_model", ""),
            "chip":      hw.get("cpu_type", ""),
            "firmware":  hw.get("os_loader_version", ""),
            "serial":    hw.get("serial_number_system", ""),
        }
    return {}


def _mac_secure_boot() -> tuple[str, Status]:
    """
    On Apple Silicon: Secure Boot is always Full Security unless changed in
    Recovery. Report as enabled. On Intel T2 Macs, check SPiBridgeDataType.
    """
    from app.utils.platform_utils import run_command
    if platform.machine() == "arm64":
        return "Full Security (Apple Silicon)", Status.PASS
    # Intel with T2 chip
    from app.utils.platform_utils import run_sp
    data = run_sp("SPiBridgeDataType", timeout=10)
    for entry in data.get("SPiBridgeDataType", []):
        policy = entry.get("ibridge_secure_boot_level", "")
        if policy:
            return f"Secure Boot: {policy}", Status.PASS
        if entry.get("_name"):
            return "Enabled (T2 Security Chip)", Status.PASS
    # Check SIP as a proxy for overall security posture
    out = run_command(["csrutil", "status"], timeout=5)
    if "enabled" in out.lower():
        return "SIP enabled (no T2/Secure Boot data)", Status.PASS
    if "disabled" in out.lower():
        return "SIP disabled", Status.WARN
    return "Unknown", Status.INFO


def _mac_tpm_equivalent() -> tuple[str, Status]:
    """macOS uses Secure Enclave (Apple Silicon) or T2 chip (Intel), not TPM."""
    if platform.machine() == "arm64":
        return "Secure Enclave (Apple Silicon)", Status.PASS
    from app.utils.platform_utils import run_sp
    data = run_sp("SPiBridgeDataType", timeout=10)
    if data.get("SPiBridgeDataType"):
        return "Apple T2 Security Chip", Status.PASS
    return "Not detected", Status.INFO


def _mac_als() -> tuple[bool, str]:
    """Check for ambient light sensor via ioreg."""
    from app.utils.platform_utils import run_command
    out = run_command(["ioreg", "-r", "-c", "AppleLMUController", "-n", "AppleLMUController"], timeout=8)
    if out.strip():
        return True, "Apple Ambient Light Sensor"
    return False, "Not detected"


# ── Run ───────────────────────────────────────────────────────────────────

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

    if IS_WINDOWS:
        bios = _bios_info_win()
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

        boot_mode, bm_status = _boot_mode_win()
        results.append(CheckResult(
            key="system_boot_mode", label="Boot Mode",
            value=boot_mode, status=bm_status,
            detail="Legacy BIOS limits security and boot options" if bm_status == Status.WARN else "",
        ))

        sec_boot, sb_status = _secure_boot_win()
        results.append(CheckResult(
            key="system_secure_boot", label="Secure Boot",
            value=sec_boot, status=sb_status,
        ))

        tpm, tpm_status = _tpm_info_win()
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

        als_found, als_name = _als_detect_win()
        results.append(CheckResult(
            key="system_als", label="Ambient Light Sensor",
            value=als_name if als_found else "Not present",
            status=Status.INFO,
        ))

    elif IS_MAC:
        fw = _mac_firmware_info()
        if fw.get("model"):
            results.append(CheckResult(
                key="system_model", label="Machine",
                value=f"{fw['model']} ({fw.get('model_id', '')})",
                status=Status.INFO,
            ))
        if fw.get("chip"):
            results.append(CheckResult(
                key="system_chip", label="Chip / CPU",
                value=fw["chip"], status=Status.INFO,
            ))
        if fw.get("firmware"):
            results.append(CheckResult(
                key="system_bios_ver", label="Firmware",
                value=fw["firmware"], status=Status.INFO,
            ))

        # macOS boot mode is always EFI
        results.append(CheckResult(
            key="system_boot_mode", label="Boot Mode",
            value="EFI (macOS default)", status=Status.PASS,
        ))

        sec, sec_status = _mac_secure_boot()
        results.append(CheckResult(
            key="system_secure_boot", label="Secure Boot",
            value=sec, status=sec_status,
        ))

        tpm, tpm_status = _mac_tpm_equivalent()
        results.append(CheckResult(
            key="system_tpm", label="Security Chip",
            value=tpm, status=tpm_status,
        ))

        results.append(CheckResult(
            key="system_activation", label="macOS Activation",
            value="N/A (macOS is tied to Apple ID, not activation key)",
            status=Status.INFO,
        ))

        als_found, als_name = _mac_als()
        results.append(CheckResult(
            key="system_als", label="Ambient Light Sensor",
            value=als_name if als_found else "Not present",
            status=Status.INFO,
        ))

    else:
        results.append(CheckResult(
            key="system_boot_mode", label="Boot Mode",
            value="Unknown", status=Status.INFO,
        ))
        results.append(CheckResult(
            key="system_secure_boot", label="Secure Boot",
            value="Unknown", status=Status.INFO,
        ))
        results.append(CheckResult(
            key="system_tpm", label="TPM",
            value="Not detected", status=Status.INFO,
        ))

    return results
