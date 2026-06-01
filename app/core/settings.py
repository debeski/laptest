from PyQt6.QtCore import QSettings, QObject, pyqtSignal


class _SettingsSignals(QObject):
    theme_changed = pyqtSignal(str)
    lang_changed = pyqtSignal(str)
    font_size_changed = pyqtSignal(int)
    accessibility_changed = pyqtSignal()


class AppSettings:
    def __init__(self):
        self._qs = QSettings("LapTest", "LapTest")
        self.signals = _SettingsSignals()

    # ── Convenience signal proxies ────────────────────────────────
    @property
    def theme_changed(self): return self.signals.theme_changed
    @property
    def lang_changed(self): return self.signals.lang_changed
    @property
    def font_size_changed(self): return self.signals.font_size_changed
    @property
    def accessibility_changed(self): return self.signals.accessibility_changed

    # ── Properties ────────────────────────────────────────────────
    @property
    def theme(self) -> str:
        return self._qs.value("theme", "dark")

    @theme.setter
    def theme(self, value: str):
        self._qs.setValue("theme", value)
        self.signals.theme_changed.emit(value)

    @property
    def language(self) -> str:
        return self._qs.value("language", "en")

    @language.setter
    def language(self, value: str):
        self._qs.setValue("language", value)
        self.signals.lang_changed.emit(value)

    @property
    def font_size(self) -> int:
        return int(self._qs.value("font_size", 13))

    @font_size.setter
    def font_size(self, value: int):
        self._qs.setValue("font_size", value)
        self.signals.font_size_changed.emit(value)

    @property
    def high_contrast(self) -> bool:
        return self._qs.value("high_contrast", False, type=bool)

    @high_contrast.setter
    def high_contrast(self, value: bool):
        self._qs.setValue("high_contrast", value)
        self.signals.accessibility_changed.emit()

    @property
    def reduce_motion(self) -> bool:
        return self._qs.value("reduce_motion", False, type=bool)

    @reduce_motion.setter
    def reduce_motion(self, value: bool):
        self._qs.setValue("reduce_motion", value)
        self.signals.accessibility_changed.emit()

    @property
    def large_text(self) -> bool:
        return self._qs.value("large_text", False, type=bool)

    @large_text.setter
    def large_text(self, value: bool):
        self._qs.setValue("large_text", value)
        self.signals.accessibility_changed.emit()


settings = AppSettings()
