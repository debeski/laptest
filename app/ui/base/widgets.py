from PyQt6.QtWidgets import (
    QPushButton, QLabel, QFrame, QLineEdit, QTextEdit,
    QComboBox, QCheckBox, QProgressBar, QScrollArea,
    QWidget, QHBoxLayout, QVBoxLayout, QSizePolicy,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QIcon

from app.core.translator import tr


# ── Helpers ────────────────────────────────────────────────────────────────

def _set_prop(widget, **props):
    for k, v in props.items():
        widget.setProperty(k, v)
    widget.style().unpolish(widget)
    widget.style().polish(widget)


# ── Buttons ────────────────────────────────────────────────────────────────

class AppButton(QPushButton):
    _variant = "secondary"

    def __init__(self, text_key: str = "", text: str = "", parent=None):
        super().__init__(parent)
        self._key = text_key
        self._static_text = text
        _set_prop(self, **{"app-btn": self._variant})
        self.retranslate()

    def retranslate(self):
        self.setText(tr(self._key) if self._key else self._static_text)


class AppPrimaryButton(AppButton):
    _variant = "primary"


class AppGhostButton(AppButton):
    _variant = "ghost"


class AppIconButton(QPushButton):
    def __init__(self, icon_text: str = "⚙", tooltip_key: str = "", parent=None):
        super().__init__(icon_text, parent)
        self._tooltip_key = tooltip_key
        _set_prop(self, **{"app-btn": "icon"})
        self.retranslate()

    def retranslate(self):
        if self._tooltip_key:
            self.setToolTip(tr(self._tooltip_key))


# ── Labels ─────────────────────────────────────────────────────────────────

class AppLabel(QLabel):
    def __init__(self, text_key: str = "", text: str = "", parent=None):
        super().__init__(parent)
        self._key = text_key
        self._static_text = text
        self.retranslate()

    def retranslate(self):
        self.setText(tr(self._key) if self._key else self._static_text)


class AppHeading(AppLabel):
    def __init__(self, text_key: str = "", text: str = "", level: int = 1, parent=None):
        super().__init__(text_key, text, parent)
        _set_prop(self, **{"app-heading": f"h{level}"})


class AppSecondaryLabel(AppLabel):
    def __init__(self, text_key: str = "", text: str = "", parent=None):
        super().__init__(text_key, text, parent)
        _set_prop(self, **{"app-text": "secondary"})


class AppMutedLabel(AppLabel):
    def __init__(self, text_key: str = "", text: str = "", parent=None):
        super().__init__(text_key, text, parent)
        _set_prop(self, **{"app-text": "muted"})


class AppAccentLabel(AppLabel):
    def __init__(self, text_key: str = "", text: str = "", parent=None):
        super().__init__(text_key, text, parent)
        _set_prop(self, **{"app-text": "accent"})


# ── Status Badge ───────────────────────────────────────────────────────────

class AppStatusBadge(QLabel):
    _STATUS_ICONS = {
        "pass": "✓", "warn": "!", "fail": "✕", "info": "i",
        "pending": "○", "running": "◷",
    }

    def __init__(self, status: str = "info", text: str = "", parent=None):
        super().__init__(parent)
        self.set_status(status, text)

    def set_status(self, status: str, text: str = ""):
        self._status = status
        icon = self._STATUS_ICONS.get(status, "")
        label_text = text or tr(f"status_{status}")
        self.setText(f"{icon} {label_text}".strip())
        _set_prop(self, **{"app-badge": status})
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)


# ── Card ───────────────────────────────────────────────────────────────────

class AppCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        _set_prop(self, **{"app-card": "true"})
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(16, 14, 16, 14)
        self._layout.setSpacing(8)

    def inner_layout(self):
        return self._layout


# ── Separator ──────────────────────────────────────────────────────────────

class AppSeparator(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        _set_prop(self, **{"app-sep": "true"})
        self.setFixedHeight(1)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)


# ── Input ──────────────────────────────────────────────────────────────────

class AppInput(QLineEdit):
    def __init__(self, placeholder_key: str = "", parent=None):
        super().__init__(parent)
        self._key = placeholder_key
        self.retranslate()

    def retranslate(self):
        if self._key:
            self.setPlaceholderText(tr(self._key))


class AppComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)


class AppCheckBox(QCheckBox):
    def __init__(self, text_key: str = "", text: str = "", parent=None):
        super().__init__(parent)
        self._key = text_key
        self._static = text
        self.retranslate()

    def retranslate(self):
        self.setText(tr(self._key) if self._key else self._static)


# ── Progress Bar ───────────────────────────────────────────────────────────

class AppProgressBar(QProgressBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTextVisible(False)
        self.setFixedHeight(6)

    def set_status(self, status: str):
        _set_prop(self, status=status)


# ── Scroll Area ────────────────────────────────────────────────────────────

class AppScrollArea(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
