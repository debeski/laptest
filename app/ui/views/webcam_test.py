import sys
import threading
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap
from app.core.translator import tr
from app.ui.base.widgets import AppHeading, AppPrimaryButton, AppButton, AppStatusBadge


class WebcamTestDialog(QDialog):
    _frame_ready = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("category_webcam"))
        self.resize(700, 480)
        self._cap = None
        self._running = False
        self._build_ui()
        self._frame_ready.connect(self._on_frame)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)
        layout.addWidget(AppHeading("category_webcam", level=2))

        self._preview = QLabel()
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setMinimumSize(640, 360)
        self._preview.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._preview.setStyleSheet(
            "background:#0a0a12;border-radius:8px;border:1px solid rgba(255,255,255,0.1);"
        )
        self._preview.setText("Camera not started")
        layout.addWidget(self._preview, 1)

        row = QHBoxLayout()
        self._start_btn = AppPrimaryButton("webcam_start")
        self._stop_btn  = AppButton("webcam_stop")
        self._stop_btn.setEnabled(False)
        self._status = AppStatusBadge("pending", "Ready")
        row.addWidget(self._start_btn)
        row.addWidget(self._stop_btn)
        row.addStretch()
        row.addWidget(self._status)
        layout.addLayout(row)

        self._start_btn.clicked.connect(self._start)
        self._stop_btn.clicked.connect(self._stop)

    def _start(self):
        try:
            import cv2
        except ImportError:
            self._status.set_status("warn")
            self._status.setText("opencv-python not installed — run: pip install opencv-python")
            return
        import cv2
        self._cap = cv2.VideoCapture(0)
        if not self._cap.isOpened():
            msg = "No camera found"
            if sys.platform == "darwin":
                msg = "No camera — grant Camera access in System Settings → Privacy & Security"
            self._status.set_status("fail")
            self._status.setText(msg)
            return
        self._running = True
        self._start_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._status.set_status("pass")
        self._status.setText("Live")
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        import cv2
        while self._running and self._cap and self._cap.isOpened():
            ret, frame = self._cap.read()
            if ret:
                self._frame_ready.emit(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

    def _on_frame(self, frame):
        h, w, ch = frame.shape
        img = QImage(frame.data, w, h, ch * w, QImage.Format.Format_RGB888)
        pix = QPixmap.fromImage(img).scaled(
            self._preview.width(), self._preview.height(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._preview.setPixmap(pix)

    def _stop(self):
        self._running = False
        if self._cap:
            self._cap.release()
            self._cap = None
        self._preview.clear()
        self._preview.setText("Camera stopped")
        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._status.set_status("pending")
        self._status.setText("Stopped")

    def closeEvent(self, event):
        self._stop()
        super().closeEvent(event)
