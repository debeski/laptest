from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QGridLayout,
    QLabel, QSizePolicy, QPushButton, QWidget,
)
from PyQt6.QtCore import Qt, pyqtSignal
from app.ui.base.widgets import AppCard, AppStatusBadge, _set_prop
from app.checkers.base import CheckResult, Status
from app.core.translator import tr

_LABEL_W = 175   # fixed label column width — guarantees alignment across all rows


class CategoryCard(AppCard):
    run_requested = pyqtSignal(str)
    launch_test   = pyqtSignal(str)

    _TEST_ICONS = {
        "input":   "⌨  Open Keyboard Test",
        "display": "🖥  Open Dead Pixel Test",
        "audio":   "🔊  Open Audio Test",
        "webcam":  "📷  Open Camera Preview",
    }

    def __init__(self, category: str, title_key: str, icon: str = "●", parent=None):
        super().__init__(parent)
        self._category  = category
        self._title_key = title_key
        self._results:  list[CheckResult] = []

        # ── Header ────────────────────────────────────────────────
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(6)

        icon_lbl = QLabel(icon)
        _set_prop(icon_lbl, **{"app-text": "accent"})

        self._title_lbl = QLabel()
        _set_prop(self._title_lbl, **{"app-heading": "h3"})

        self._status_badge = AppStatusBadge("pending")

        self._run_btn = QPushButton("▶")
        self._run_btn.setFixedSize(26, 26)
        self._run_btn.setToolTip("Run this test")
        self._run_btn.setStyleSheet(
            "QPushButton{background:transparent;border:1px solid rgba(255,255,255,0.15);"
            "border-radius:5px;font-size:10px;}"
            "QPushButton:hover{background:rgba(255,255,255,0.1);}"
        )
        self._run_btn.clicked.connect(lambda: self.run_requested.emit(self._category))

        header.addWidget(icon_lbl)
        header.addWidget(self._title_lbl, 1)
        header.addWidget(self._status_badge)
        header.addWidget(self._run_btn)

        from app.ui.base.widgets import AppSeparator
        self.inner_layout().addLayout(header)
        self.inner_layout().addWidget(AppSeparator())

        # ── Results grid (guarantees column alignment) ────────────
        self._grid = QGridLayout()
        self._grid.setContentsMargins(0, 4, 0, 2)
        self._grid.setHorizontalSpacing(12)
        self._grid.setVerticalSpacing(3)
        self._grid.setColumnMinimumWidth(0, _LABEL_W)
        self._grid.setColumnMinimumWidth(2, 72)
        self._grid.setColumnStretch(1, 1)

        grid_wrap = QWidget()
        grid_wrap.setLayout(self._grid)
        self.inner_layout().addWidget(grid_wrap)

        # ── Optional launch button ────────────────────────────────
        if category in self._TEST_ICONS:
            self._launch_btn = QPushButton(self._TEST_ICONS[category])
            self._launch_btn.setProperty("app-btn", "ghost")
            self._launch_btn.style().unpolish(self._launch_btn)
            self._launch_btn.style().polish(self._launch_btn)
            self._launch_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._launch_btn.clicked.connect(lambda: self.launch_test.emit(self._category))
            self.inner_layout().addSpacing(4)
            self.inner_layout().addWidget(self._launch_btn)

        self.retranslate()

    def retranslate(self):
        self._title_lbl.setText(tr(self._title_key))

    # ── Data ──────────────────────────────────────────────────────

    def set_results(self, results: list[CheckResult]):
        self._results = results
        # Clear old grid contents
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for row, r in enumerate(results):
            lbl = QLabel(r.label)
            lbl.setFixedWidth(_LABEL_W)
            lbl.setWordWrap(False)
            _set_prop(lbl, **{"app-text": "secondary"})

            val = QLabel(r.value)
            val.setWordWrap(True)
            val.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

            badge = AppStatusBadge(r.status.value)
            if r.detail:
                lbl.setToolTip(r.detail)
                val.setToolTip(r.detail)

            self._grid.addWidget(lbl,   row, 0, Qt.AlignmentFlag.AlignTop)
            self._grid.addWidget(val,   row, 1, Qt.AlignmentFlag.AlignTop)
            self._grid.addWidget(badge, row, 2, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)

        self._update_status(results)

    def _update_status(self, results: list[CheckResult]):
        if not results:
            self._status_badge.set_status("pending")
            return
        statuses = [r.status for r in results]
        if any(s == Status.FAIL for s in statuses):
            self._status_badge.set_status("fail")
        elif any(s == Status.WARN for s in statuses):
            self._status_badge.set_status("warn")
        elif any(s == Status.PASS for s in statuses):
            self._status_badge.set_status("pass")
        else:
            self._status_badge.set_status("info")

    def is_all_not_detected(self) -> bool:
        if not self._results:
            return False
        neg = ("not detected", "not present", "no ", "none", "could not", "not accessible")
        return all(
            r.status == Status.INFO and any(x in r.value.lower() for x in neg)
            for r in self._results
        )

    def set_running(self):
        self._status_badge.set_status("running")
        self._status_badge.setText("◷ Running")

    def set_pending(self):
        self._status_badge.set_status("pending")
        self._status_badge.setText("○ Pending")

    # Expose for export compatibility
    @property
    def _rows(self):
        class _Proxy:
            def __init__(self, results):
                self._results = results
            def values(self):
                return [type("R", (), {"_result": r})() for r in self._results]
        return _Proxy(self._results)
