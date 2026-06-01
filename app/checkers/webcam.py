import platform
from app.checkers.base import CheckResult, Status


def _detect_cameras() -> list[dict]:
    cameras = []
    if platform.system() == "Windows":
        try:
            import wmi
            c = wmi.WMI()
            for dev in c.Win32_PnPEntity():
                name = (dev.Name or "").lower()
                caption = (dev.Caption or "").lower()
                if any(k in name or k in caption for k in ("camera", "webcam", "integrated camera", "uvc")):
                    cameras.append({
                        "name": (dev.Name or dev.Caption or "Unknown Camera").strip(),
                        "status": (dev.Status or "").strip(),
                    })
        except Exception:
            pass
    if not cameras:
        try:
            import cv2
            for idx in range(3):
                cap = cv2.VideoCapture(idx)
                if cap.isOpened():
                    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    cameras.append({
                        "name":   f"Camera {idx}",
                        "width":  w, "height": h,
                        "fps":    fps,
                        "status": "OK",
                    })
                    cap.release()
        except ImportError:
            pass
    return cameras


def run() -> list[CheckResult]:
    results = []
    cameras = _detect_cameras()

    if not cameras:
        results.append(CheckResult(
            key="webcam_model", label="Webcam",
            value="No camera detected", status=Status.WARN,
            detail="Camera may not be present or driver is missing"
        ))
        return results

    for i, cam in enumerate(cameras):
        pfx = f"Camera {i + 1}: " if len(cameras) > 1 else ""
        status = Status.PASS if cam.get("status") == "OK" else Status.WARN
        results.append(CheckResult(
            key="webcam_model",
            label=f"{pfx}Model",
            value=cam["name"],
            status=status,
        ))
        if "width" in cam and cam["width"]:
            results.append(CheckResult(
                key="webcam_resolution",
                label=f"{pfx}Resolution",
                value=f"{cam['width']} × {cam['height']}",
                status=Status.INFO,
            ))
        if "fps" in cam and cam["fps"]:
            results.append(CheckResult(
                key="webcam_fps",
                label=f"{pfx}FPS",
                value=f"{cam['fps']:.0f} fps",
                status=Status.INFO,
            ))

    results.append(CheckResult(
        key="webcam_preview",
        label="Camera Preview",
        value="Use preview in Camera tab",
        status=Status.INFO,
        detail="Click 'Start Camera' in the Camera tab to verify the image",
    ))

    return results
