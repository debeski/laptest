from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QStackedWidget
from app.core.settings import settings
from app.core.translator import tr, set_language, is_rtl
from app.core import theme as theme_module
from app.ui.views.dashboard import DashboardView
from app.ui.views.settings_view import SettingsView
from app.utils.workers import MultiWorker, Worker
from app.checkers.base import Status

import app.checkers.storage       as c_storage
import app.checkers.memory        as c_memory
import app.checkers.cpu           as c_cpu
import app.checkers.gpu           as c_gpu
import app.checkers.display       as c_display
import app.checkers.battery       as c_battery
import app.checkers.input_devices as c_input
import app.checkers.audio         as c_audio
import app.checkers.webcam        as c_webcam
import app.checkers.network       as c_network
import app.checkers.ports         as c_ports
import app.checkers.system        as c_system
import app.checkers.thermal       as c_thermal

_CHECKER_MAP = {
    "storage": c_storage.run,
    "memory":  c_memory.run,
    "cpu":     c_cpu.run,
    "gpu":     c_gpu.run,
    "display": c_display.run,
    "battery": c_battery.run,
    "input":   c_input.run,
    "audio":   c_audio.run,
    "webcam":  c_webcam.run,
    "network": c_network.run,
    "ports":   c_ports.run,
    "system":  c_system.run,
    "thermal": c_thermal.run,
}

_HIDEABLE = {"webcam", "battery", "thermal"}


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(tr("app_title"))
        self.setMinimumSize(960, 640)
        self.resize(1200, 780)
        self._worker: MultiWorker | None = None
        self._single_workers: list[Worker] = []
        self._open_dialogs: dict = {}

        set_language(settings.language)
        theme_module.apply_theme(settings.theme)
        self._apply_qss()
        self._setup_ui()
        self._connect_settings()
        self._apply_direction()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._stack = QStackedWidget()
        self._dashboard     = DashboardView()
        self._settings_view = SettingsView()
        self._stack.addWidget(self._dashboard)     # 0
        self._stack.addWidget(self._settings_view) # 1
        layout.addWidget(self._stack)

        self._dashboard.run_requested.connect(self._start_all_checks)
        self._dashboard.stop_requested.connect(self._stop_checks)
        self._dashboard.run_category.connect(self._run_single)
        self._dashboard.launch_test.connect(self._open_test_dialog)
        self._dashboard.settings_requested.connect(self._show_settings)
        self._settings_view.back_requested.connect(self._show_dashboard)

    def _connect_settings(self):
        settings.theme_changed.connect(self._on_theme)
        settings.lang_changed.connect(self._on_lang)
        settings.font_size_changed.connect(lambda _: self._apply_qss())
        settings.accessibility_changed.connect(self._apply_qss)

    # ── Navigation ────────────────────────────────────────────────

    def _show_settings(self):
        self._stack.setCurrentIndex(1)

    def _show_dashboard(self):
        self._stack.setCurrentIndex(0)

    # ── Interactive test dialogs ──────────────────────────────────

    def _open_test_dialog(self, category: str):
        from app.ui.views.keyboard_test  import KeyboardTestDialog
        from app.ui.views.deadpixel_test import DeadPixelDialog
        from app.ui.views.audio_test     import AudioTestDialog
        from app.ui.views.webcam_test    import WebcamTestDialog

        cls_map = {
            "input":   KeyboardTestDialog,
            "display": DeadPixelDialog,
            "audio":   AudioTestDialog,
            "webcam":  WebcamTestDialog,
        }
        cls = cls_map.get(category)
        if not cls:
            return
        if category in self._open_dialogs and self._open_dialogs[category].isVisible():
            self._open_dialogs[category].raise_()
            return
        dlg = cls(self)
        self._open_dialogs[category] = dlg
        dlg.show()

    # ── Single-category run ───────────────────────────────────────

    def _run_single(self, category: str):
        fn = _CHECKER_MAP.get(category)
        if not fn:
            return
        card = self._dashboard.card(category)
        if card:
            card.set_running()
        w = Worker(fn)
        w.result.connect(lambda res, c=category: self._on_single_done(c, res))
        w.start()
        self._single_workers.append(w)
        self._single_workers = [x for x in self._single_workers if x.isRunning()]

    def _on_single_done(self, category: str, results: list):
        self._dashboard.set_results(category, results)
        self._maybe_hide(category, results)

    # ── Run all ───────────────────────────────────────────────────

    def _start_all_checks(self):
        if self._worker and self._worker.isRunning():
            return
        self._dashboard.set_all_pending()
        self._dashboard.set_running_state(True)
        self._worker = MultiWorker(list(_CHECKER_MAP.items()))
        self._worker.progress.connect(self._on_progress)
        self._worker.step_done.connect(self._on_step_done)
        self._worker.all_done.connect(self._on_all_done)
        self._worker.start()

    def _stop_checks(self):
        if self._worker:
            self._worker.stop()
        self._dashboard.set_running_state(False)

    def _on_progress(self, idx: int, total: int, key: str):
        self._dashboard.set_running(key)

    def _on_step_done(self, key: str, results: list):
        self._dashboard.set_results(key, results)
        self._maybe_hide(key, results)

    def _on_all_done(self):
        self._dashboard.set_running_state(False)

    # ── Helpers ───────────────────────────────────────────────────

    def _maybe_hide(self, category: str, results: list):
        pass   # sidebar removed — nothing to hide

    # ── Theme / lang ──────────────────────────────────────────────

    def _on_theme(self, name: str):
        theme_module.apply_theme(name)
        self._apply_qss()

    def _on_lang(self, lang: str):
        set_language(lang)
        self._apply_direction()
        self.setWindowTitle(tr("app_title"))
        self._dashboard.retranslate()
        self._settings_view.retranslate()

    def _apply_qss(self):
        t = theme_module.current() or theme_module.apply_theme(settings.theme)
        fs = settings.font_size + (2 if settings.large_text else 0)
        qss = theme_module.build_stylesheet(t, font_size=fs)
        if settings.high_contrast:
            qss += "QWidget{border:1px solid white!important;}"
        self.setStyleSheet(qss)

    def _apply_direction(self):
        from PyQt6.QtCore import Qt
        d = Qt.LayoutDirection.RightToLeft if is_rtl() else Qt.LayoutDirection.LeftToRight
        self.setLayoutDirection(d)

    def closeEvent(self, event):
        if self._worker and self._worker.isRunning():
            self._worker.stop()
            self._worker.wait(2000)
        super().closeEvent(event)
