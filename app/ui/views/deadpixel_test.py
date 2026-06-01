from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PyQt6.QtCore import Qt
from app.core.translator import tr
from app.ui.base.widgets import AppCard, AppHeading, AppSecondaryLabel, AppPrimaryButton, _set_prop

_COLORS = [
    ("#000000", "Black"),
    ("#ffffff", "White"),
    ("#ff0000", "Red"),
    ("#00ff00", "Green"),
    ("#0000ff", "Blue"),
    ("#ffff00", "Yellow"),
    ("#ff00ff", "Magenta"),
    ("#00ffff", "Cyan"),
]


class _FullscreenColor(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self._idx = 0
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._hint = QLabel()
        self._hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._hint)
        self._apply()

    def _apply(self):
        hex_c, name = _COLORS[self._idx]
        self.setStyleSheet(f"background:{hex_c};")
        text_color = "#000" if hex_c in ("#ffffff", "#ffff00", "#00ffff") else "#fff"
        self._hint.setStyleSheet(f"font-size:15px;color:{text_color};background:transparent;")
        self._hint.setText(f"{name}  —  Click or any key to cycle  ·  ESC to exit")

    def _next(self):
        self._idx = (self._idx + 1) % len(_COLORS)
        self._apply()

    def mousePressEvent(self, event): self._next()
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            self._next()


class DeadPixelDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("display_dead_pixels"))
        self.resize(500, 340)
        self._fs = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)
        layout.addWidget(AppHeading("display_dead_pixels", level=2))

        desc = AppSecondaryLabel(
            text="Fill the screen with solid colors to detect dead or stuck pixels. "
                 "Look for dots that don't change color with the background."
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Color swatches preview
        swatch_card = AppCard()
        swatch_row = QHBoxLayout()
        for hex_c, name in _COLORS:
            sw = QFrame()
            sw.setFixedSize(40, 40)
            sw.setStyleSheet(
                f"background:{hex_c};border-radius:5px;"
                "border:1px solid rgba(255,255,255,0.15);"
            )
            sw.setToolTip(name)
            swatch_row.addWidget(sw)
        swatch_row.addStretch()
        swatch_card.inner_layout().addLayout(swatch_row)
        layout.addWidget(swatch_card)

        btn = AppPrimaryButton(text="Launch Fullscreen Dead Pixel Test")
        btn.clicked.connect(self._launch)
        layout.addWidget(btn)

        hint = AppSecondaryLabel(
            text="Click or press any key to cycle through colors. Press ESC to exit."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)
        layout.addStretch()

    def _launch(self):
        self._fs = _FullscreenColor(self)
        self._fs.showFullScreen()
        self._fs.setFocus()
