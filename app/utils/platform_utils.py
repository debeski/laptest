import sys
import os
import platform
import subprocess

IS_WINDOWS = sys.platform == "win32"
IS_MAC     = sys.platform == "darwin"
IS_LINUX   = sys.platform.startswith("linux")

# Used by every subprocess call to suppress the black CMD window on Windows
_NO_WINDOW = 0x08000000  # CREATE_NO_WINDOW


def run_command(cmd, timeout: int = 10) -> str:
    """
    Run cmd (str → shell=True, list → shell=False) with no visible window on Windows.
    Returns stdout stripped, or '' on any error.
    """
    kwargs: dict = dict(capture_output=True, text=True, timeout=timeout)
    if IS_WINDOWS:
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        kwargs["startupinfo"] = si
        kwargs["creationflags"] = _NO_WINDOW
    kwargs["shell"] = isinstance(cmd, str)
    try:
        return subprocess.run(cmd, **kwargs).stdout.strip()
    except Exception:
        return ""


def run_ps(command: str, timeout: int = 10) -> str:
    """Run a PowerShell command, returning stdout."""
    return run_command(
        ["powershell", "-NonInteractive", "-NoProfile", "-Command", command],
        timeout=timeout,
    )


def run_sp(datatype: str, timeout: int = 15) -> dict:
    """Run system_profiler <datatype> -json on macOS and return the parsed dict."""
    if not IS_MAC:
        return {}
    import json as _json
    out = run_command(["system_profiler", datatype, "-json"], timeout=timeout)
    try:
        return _json.loads(out)
    except Exception:
        return {}


def get_wmi(namespace: str = "root/cimv2"):
    if IS_WINDOWS:
        try:
            import wmi
            return wmi.WMI(namespace=namespace)
        except Exception:
            return None
    return None


def reg_read(path: str, key: str) -> str | None:
    if not IS_WINDOWS:
        return None
    try:
        import winreg
        parts = path.split("\\", 1)
        hive_map = {
            "HKEY_LOCAL_MACHINE": winreg.HKEY_LOCAL_MACHINE,
            "HKLM":               winreg.HKEY_LOCAL_MACHINE,
            "HKEY_CURRENT_USER":  winreg.HKEY_CURRENT_USER,
            "HKCU":               winreg.HKEY_CURRENT_USER,
        }
        hive = hive_map.get(parts[0], winreg.HKEY_LOCAL_MACHINE)
        sub  = parts[1] if len(parts) > 1 else ""
        with winreg.OpenKey(hive, sub) as k:
            val, _ = winreg.QueryValueEx(k, key)
            return str(val)
    except Exception:
        return None


def is_admin() -> bool:
    if IS_WINDOWS:
        try:
            import ctypes
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False
    return os.getuid() == 0
