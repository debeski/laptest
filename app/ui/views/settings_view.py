from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QFrame, QSpinBox,
)
from PyQt6.QtCore import Qt, pyqtSignal
from app.core.settings import settings
from app.core.translator import tr
from app.ui.base.widgets import (
    AppCard, AppHeading, AppLabel, AppSecondaryLabel,
    AppComboBox, AppCheckBox, AppSeparator,
    AppButton, AppPrimaryButton, _set_prop,
)

_LANGUAGES = [("en", "lang_en"), ("ar", "lang_ar"), ("fr", "lang_fr")]
_THEMES    = [("dark", "theme_dark"), ("light", "theme_light")]


class SettingRow(QWidget):
    def __init__(self, label_key: str, control: QWidget, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 6, 0, 6)
        layout.setSpacing(16)
        self._lbl = QLabel()
        _set_prop(self._lbl, **{"app-text": "secondary"})
        self._lbl_key = label_key
        self._lbl.setFixedWidth(180)
        layout.addWidget(self._lbl)
        layout.addWidget(control, 1)
        self.retranslate()

    def retranslate(self):
        self._lbl.setText(tr(self._lbl_key))


class SettingsView(QWidget):
    back_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._connect()

    def _setup_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(28, 20, 28, 28)
        layout.setSpacing(16)
        scroll.setWidget(inner)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        # ── Header with back button ───────────────────────────────
        hdr = QHBoxLayout()
        self._back_btn = AppButton(text="← Back")
        self._back_btn.clicked.connect(self.back_requested.emit)
        self._title = AppHeading("settings_title", level=1)
        hdr.addWidget(self._back_btn)
        hdr.addSpacing(12)
        hdr.addWidget(self._title, 1)
        layout.addLayout(hdr)
        layout.addSpacing(4)

        # ── Appearance ────────────────────────────────────────────
        self._app_card = AppCard()
        ai = self._app_card.inner_layout()
        self._app_heading = AppHeading("settings_appearance", level=2)
        ai.addWidget(self._app_heading)
        ai.addWidget(AppSeparator())

        self._theme_combo = AppComboBox()
        for val, key in _THEMES:
            self._theme_combo.addItem(tr(key), val)
        self._theme_combo.setCurrentIndex(
            max(0, self._theme_combo.findData(settings.theme))
        )
        self._theme_row = SettingRow("settings_theme", self._theme_combo)
        ai.addWidget(self._theme_row)

        self._lang_combo = AppComboBox()
        for val, key in _LANGUAGES:
            self._lang_combo.addItem(tr(key), val)
        self._lang_combo.setCurrentIndex(
            max(0, self._lang_combo.findData(settings.language))
        )
        self._lang_row = SettingRow("settings_language", self._lang_combo)
        ai.addWidget(self._lang_row)

        # Font size — explicit spin box with enough room for buttons
        self._font_spin = QSpinBox()
        self._font_spin.setRange(10, 20)
        self._font_spin.setValue(settings.font_size)
        self._font_spin.setMinimumWidth(100)
        self._font_spin.setMaximumWidth(120)
        self._font_row = SettingRow("settings_font_size", self._font_spin)
        # Wrap in HBox so spinbox doesn't stretch and buttons stay visible
        font_wrap = QHBoxLayout()
        font_wrap.setContentsMargins(0, 0, 0, 0)
        font_wrap.addWidget(self._font_spin)
        font_wrap.addStretch()
        font_widget = QWidget()
        font_widget.setLayout(font_wrap)
        self._font_row2 = SettingRow("settings_font_size", font_widget)
        ai.addWidget(self._font_row2)

        layout.addWidget(self._app_card)

        # ── Accessibility ─────────────────────────────────────────
        self._acc_card = AppCard()
        aci = self._acc_card.inner_layout()
        self._acc_heading = AppHeading("settings_accessibility", level=2)
        aci.addWidget(self._acc_heading)
        aci.addWidget(AppSeparator())
        self._high_contrast = AppCheckBox("settings_high_contrast")
        self._high_contrast.setChecked(settings.high_contrast)
        self._reduce_motion = AppCheckBox("settings_reduce_motion")
        self._reduce_motion.setChecked(settings.reduce_motion)
        self._large_text    = AppCheckBox("settings_large_text")
        self._large_text.setChecked(settings.large_text)
        aci.addWidget(self._high_contrast)
        aci.addWidget(self._reduce_motion)
        aci.addWidget(self._large_text)
        layout.addWidget(self._acc_card)
        layout.addStretch()

    def _connect(self):
        self._theme_combo.currentIndexChanged.connect(
            lambda i: setattr(settings, "theme", self._theme_combo.itemData(i) or settings.theme)
        )
        self._lang_combo.currentIndexChanged.connect(
            lambda i: setattr(settings, "language", self._lang_combo.itemData(i) or settings.language)
        )
        self._font_spin.valueChanged.connect(lambda v: setattr(settings, "font_size", v))
        self._high_contrast.toggled.connect(lambda v: setattr(settings, "high_contrast", v))
        self._reduce_motion.toggled.connect(lambda v: setattr(settings, "reduce_motion", v))
        self._large_text.toggled.connect(lambda v: setattr(settings, "large_text", v))

    def retranslate(self):
        self._title.retranslate()
        self._app_heading.retranslate()
        self._acc_heading.retranslate()
        self._theme_row.retranslate()
        self._lang_row.retranslate()
        self._font_row2.retranslate()
        for cb in (self._high_contrast, self._reduce_motion, self._large_text):
            cb.retranslate()
        for i, (_, key) in enumerate(_THEMES):
            self._theme_combo.setItemText(i, tr(key))
        for i, (_, key) in enumerate(_LANGUAGES):
            self._lang_combo.setItemText(i, tr(key))
