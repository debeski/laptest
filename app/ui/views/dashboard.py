from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QFrame,
    QLabel, QGridLayout,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from app.core.translator import tr
from app.ui.base.widgets import (
    AppPrimaryButton, AppButton, AppIconButton, AppSeparator, _set_prop,
)
from app.ui.components.result_card import CategoryCard

_CATEGORIES = [
    ("storage",  "category_storage",  "💾"),
    ("memory",   "category_memory",   "🧠"),
    ("cpu",      "category_cpu",      "⚡"),
    ("gpu",      "category_gpu",      "🎮"),
    ("display",  "category_display",  "🖥"),
    ("battery",  "category_battery",  "🔋"),
    ("input",    "category_input",    "⌨"),
    ("audio",    "category_audio",    "🔊"),
    ("webcam",   "category_webcam",   "📷"),
    ("network",  "category_network",  "📶"),
    ("ports",    "category_ports",    "🔌"),
    ("system",   "category_system",   "⚙"),
    ("thermal",  "category_thermal",  "🌡"),
]


class ScoreTile(QFrame):
    def __init__(self, icon: str, label_key: str, parent=None):
        super().__init__(parent)
        _set_prop(self, **{"app-card": "true"})
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._icon_lbl = QLabel(icon)
        self._icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_lbl.setStyleSheet("font-size: 20px;")

        self._value = QLabel("—")
        self._value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _set_prop(self._value, **{"app-heading": "h2"})

        self._label = QLabel()
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _set_prop(self._label, **{"app-text": "muted"})
        self._label_key = label_key

        layout.addWidget(self._icon_lbl)
        layout.addWidget(self._value)
        layout.addWidget(self._label)
        self.retranslate()

    def set_value(self, v: str): self._value.setText(v)
    def retranslate(self): self._label.setText(tr(self._label_key))


class DashboardView(QWidget):
    run_requested  = pyqtSignal()
    stop_requested = pyqtSignal()
    run_category   = pyqtSignal(str)
    launch_test    = pyqtSignal(str)
    settings_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cards: dict[str, CategoryCard] = {}
        self._running = False
        self._setup_ui()

    def _setup_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        # ── Toolbar ───────────────────────────────────────────────
        toolbar = QFrame()
        toolbar.setFixedHeight(58)
        toolbar.setStyleSheet(
            "QFrame{border-bottom:1px solid rgba(255,255,255,0.08);background:transparent;}"
        )
        tb = QHBoxLayout(toolbar)
        tb.setContentsMargins(20, 0, 16, 0)
        tb.setSpacing(8)

        self._page_title = QLabel()
        _set_prop(self._page_title, **{"app-heading": "h2"})

        self._run_btn     = AppPrimaryButton("run_all")
        self._run_btn.setMinimumWidth(148)
        self._export_btn  = AppButton("export_report")
        self._settings_btn = AppIconButton("⚙", tooltip_key="settings")
        self._settings_btn.setFixedSize(36, 36)

        tb.addWidget(self._page_title, 1)
        tb.addWidget(self._export_btn)
        tb.addWidget(self._run_btn)
        tb.addWidget(self._settings_btn)
        main.addWidget(toolbar)

        # ── Score tiles ───────────────────────────────────────────
        summary = QFrame()
        sl = QHBoxLayout(summary)
        sl.setContentsMargins(20, 10, 20, 10)
        sl.setSpacing(12)
        self._tile_pass  = ScoreTile("✅", "tests_passed")
        self._tile_warn  = ScoreTile("⚠️",  "tests_warned")
        self._tile_fail  = ScoreTile("❌", "tests_failed")
        self._tile_score = ScoreTile("🏆", "overall_score")
        for t in (self._tile_pass, self._tile_warn, self._tile_fail, self._tile_score):
            sl.addWidget(t, 1)
        main.addWidget(summary)
        main.addWidget(AppSeparator())

        # ── Scrollable 2-column grid ──────────────────────────────
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)

        grid_wrap = QWidget()
        self._grid = QGridLayout(grid_wrap)
        self._grid.setContentsMargins(20, 16, 20, 20)
        self._grid.setSpacing(14)
        self._grid.setColumnStretch(0, 1)
        self._grid.setColumnStretch(1, 1)

        for i, (cat, key, icon) in enumerate(_CATEGORIES):
            card = CategoryCard(cat, key, icon)
            card.run_requested.connect(self.run_category.emit)
            card.launch_test.connect(self.launch_test.emit)
            self._cards[cat] = card
            self._grid.addWidget(card, i // 2, i % 2)

        self._scroll.setWidget(grid_wrap)
        main.addWidget(self._scroll, 1)

        self._run_btn.clicked.connect(self._on_run)
        self._export_btn.clicked.connect(self._export)
        self._settings_btn.clicked.connect(self.settings_requested.emit)
        self.retranslate()

    # ── Public API ────────────────────────────────────────────────

    def retranslate(self):
        self._page_title.setText(tr("app_title"))
        self._run_btn.retranslate()
        self._export_btn.retranslate()
        for t in (self._tile_pass, self._tile_warn, self._tile_fail, self._tile_score):
            t.retranslate()
        for card in self._cards.values():
            card.retranslate()

    def scroll_to_card(self, category: str):
        if category in self._cards:
            card = self._cards[category]
            QTimer.singleShot(30, lambda: self._scroll.ensureWidgetVisible(card))

    def set_results(self, category: str, results: list):
        if category in self._cards:
            self._cards[category].set_results(results)
        self._update_summary()

    def set_running(self, category: str):
        if category in self._cards:
            self._cards[category].set_running()

    def set_all_pending(self):
        for card in self._cards.values():
            card.set_pending()

    def set_running_state(self, running: bool):
        self._running = running
        self._run_btn.setText(f"⏹  {tr('stop')}" if running else tr("run_all"))

    def card(self, category: str) -> CategoryCard | None:
        return self._cards.get(category)

    # ── Private ───────────────────────────────────────────────────

    def _on_run(self):
        if self._running:
            self.stop_requested.emit()
        else:
            self.run_requested.emit()

    def _update_summary(self):
        from app.checkers.base import Status
        all_r = [r for card in self._cards.values() for r in card._results]
        passed = sum(1 for r in all_r if r.status == Status.PASS)
        warned = sum(1 for r in all_r if r.status == Status.WARN)
        failed = sum(1 for r in all_r if r.status == Status.FAIL)
        total  = passed + warned + failed
        score  = int(100 * (passed + 0.5 * warned) / total) if total else 0
        self._tile_pass.set_value(str(passed))
        self._tile_warn.set_value(str(warned))
        self._tile_fail.set_value(str(failed))
        self._tile_score.set_value(f"{score}%")

    def _export(self):
        from PyQt6.QtWidgets import QFileDialog
        import json, datetime
        path, _ = QFileDialog.getSaveFileName(
            self, tr("export_report"),
            f"laptest_report_{datetime.date.today()}.json",
            "JSON Files (*.json);;All Files (*)",
        )
        if not path:
            return
        data = {
            cat: [r.as_dict() for r in card._results]
            for cat, card in self._cards.items()
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
