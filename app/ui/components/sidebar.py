from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QWidget, QScrollArea,
)
from PyQt6.QtCore import Qt, pyqtSignal
from app.core.translator import tr
from app.ui.base.widgets import AppSeparator, _set_prop


_CATEGORIES = [
    ("category_storage",  "💾", "storage"),
    ("category_memory",   "🧠", "memory"),
    ("category_cpu",      "⚡", "cpu"),
    ("category_gpu",      "🎮", "gpu"),
    ("category_display",  "🖥",  "display"),
    ("category_battery",  "🔋", "battery"),
    ("category_input",    "⌨",  "input"),
    ("category_audio",    "🔊", "audio"),
    ("category_webcam",   "📷", "webcam"),
    ("category_network",  "📶", "network"),
    ("category_ports",    "🔌", "ports"),
    ("category_system",   "⚙",  "system"),
    ("category_thermal",  "🌡", "thermal"),
]

_STATUS_ICONS = {
    "pass": " ✓", "warn": " !", "fail": " ✕",
    "running": " ◷", "pending": "",
}


class NavButton(QPushButton):
    def __init__(self, label_key: str, icon: str, category: str, parent=None):
        super().__init__(parent)
        self._key = label_key
        self._icon = icon
        self._category = category
        self._status_suffix = ""
        _set_prop(self, **{"app-nav": "true"})
        self.retranslate()

    def retranslate(self):
        # Escape & so Qt doesn't treat it as a keyboard accelerator
        label = tr(self._key).replace("&", "&&")
        self.setText(f"  {self._icon}  {label}{self._status_suffix}")

    def set_active(self, active: bool):
        _set_prop(self, **{"app-nav": "true", "active": "true" if active else "false"})

    def set_status(self, status: str):
        self._status_suffix = _STATUS_ICONS.get(status, "")
        self.retranslate()


class Sidebar(QFrame):
    category_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(220)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 12, 8, 12)
        outer.setSpacing(0)

        # Brand
        brand = QHBoxLayout()
        brand.setContentsMargins(8, 4, 8, 8)
        icon_lbl = QLabel("🔍")
        icon_lbl.setStyleSheet("font-size: 22px;")
        self._brand_title = QLabel()
        _set_prop(self._brand_title, **{"app-heading": "h2"})
        brand.addWidget(icon_lbl)
        brand.addWidget(self._brand_title)
        brand.addStretch()
        outer.addLayout(brand)
        outer.addWidget(AppSeparator())
        outer.addSpacing(8)

        # Scrollable nav
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        nav_widget = QWidget()
        self._nav_layout = QVBoxLayout(nav_widget)
        self._nav_layout.setContentsMargins(0, 0, 0, 0)
        self._nav_layout.setSpacing(2)

        self._buttons: dict[str, NavButton] = {}

        for key, icon, cat in _CATEGORIES:
            btn = NavButton(key, icon, cat)
            btn.clicked.connect(lambda checked, c=cat: self._on_nav(c))
            self._buttons[cat] = btn
            self._nav_layout.addWidget(btn)

        self._nav_layout.addStretch()
        scroll.setWidget(nav_widget)
        outer.addWidget(scroll, 1)

        # Settings pinned at bottom
        outer.addWidget(AppSeparator())
        outer.addSpacing(4)
        self._settings_btn = NavButton("settings", "⚙", "settings_nav")
        self._settings_btn.clicked.connect(lambda: self._on_nav("settings_nav"))
        self._buttons["settings_nav"] = self._settings_btn
        outer.addWidget(self._settings_btn)

        self._active: str = ""
        self.retranslate()

    def retranslate(self):
        self._brand_title.setText(tr("app_title"))
        for btn in self._buttons.values():
            btn.retranslate()

    def _on_nav(self, category: str):
        self.set_active(category)
        self.category_selected.emit(category)

    def set_active(self, category: str):
        self._active = category
        for cat, btn in self._buttons.items():
            btn.set_active(cat == category)

    def set_category_status(self, category: str, status: str):
        if category in self._buttons:
            self._buttons[category].set_status(status)

    def hide_category(self, category: str):
        if category in self._buttons:
            self._buttons[category].setVisible(False)

    def show_category(self, category: str):
        if category in self._buttons:
            self._buttons[category].setVisible(True)
