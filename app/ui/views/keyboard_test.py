import sys
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent
from app.core.translator import tr
from app.ui.base.widgets import (
    AppHeading, AppSecondaryLabel, AppPrimaryButton, AppButton, AppCard, _set_prop,
)

# ── Platform-specific layouts ─────────────────────────────────────────────

_KEY_LAYOUT_WIN = [
    ["Esc", "F1","F2","F3","F4","F5","F6","F7","F8","F9","F10","F11","F12","Del"],
    ["`","1","2","3","4","5","6","7","8","9","0","-","=","Backspace"],
    ["Tab","Q","W","E","R","T","Y","U","I","O","P","[","]","\\"],
    ["CapsLock","A","S","D","F","G","H","J","K","L",";","'","Enter"],
    ["Shift","Z","X","C","V","B","N","M",",",".","/","Shift"],
    ["Ctrl","Win","Alt","Space","Alt","Fn","Ctrl"],
]
_WIDE_WIN = {"Backspace","Tab","CapsLock","Enter","Shift","Space","Ctrl","Win","Alt","Fn"}

_KEY_LAYOUT_MAC = [
    ["Esc", "F1","F2","F3","F4","F5","F6","F7","F8","F9","F10","F11","F12"],
    ["`","1","2","3","4","5","6","7","8","9","0","-","=","Delete"],
    ["Tab","Q","W","E","R","T","Y","U","I","O","P","[","]","\\"],
    ["CapsLock","A","S","D","F","G","H","J","K","L",";","'","Return"],
    ["Shift","Z","X","C","V","B","N","M",",",".","/","Shift"],
    ["Ctrl","Option","Cmd","Space","Cmd","Option","←","→","↑","↓"],
]
_WIDE_MAC = {"Delete","Tab","CapsLock","Return","Shift","Space","Ctrl","Option","Cmd"}

_IS_MAC = sys.platform == "darwin"
_KEY_LAYOUT = _KEY_LAYOUT_MAC if _IS_MAC else _KEY_LAYOUT_WIN
_WIDE       = _WIDE_MAC       if _IS_MAC else _WIDE_WIN

# ── Key → layout-label mapping ────────────────────────────────────────────

_SPECIAL_MAP_WIN = {
    Qt.Key.Key_Escape:    "Esc",
    Qt.Key.Key_Tab:       "Tab",
    Qt.Key.Key_CapsLock:  "CapsLock",
    Qt.Key.Key_Return:    "Enter",
    Qt.Key.Key_Backspace: "Backspace",
    Qt.Key.Key_Delete:    "Del",
    Qt.Key.Key_Space:     "Space",
    Qt.Key.Key_Control:   "Ctrl",
    Qt.Key.Key_Alt:       "Alt",
    Qt.Key.Key_Shift:     "Shift",
    Qt.Key.Key_Meta:      "Win",
    **{getattr(Qt.Key, f"Key_F{n}"): f"F{n}" for n in range(1, 13)},
    Qt.Key.Key_QuoteLeft:    "`",
    Qt.Key.Key_Minus:        "-",
    Qt.Key.Key_Equal:        "=",
    Qt.Key.Key_BracketLeft:  "[",
    Qt.Key.Key_BracketRight: "]",
    Qt.Key.Key_Backslash:    "\\",
    Qt.Key.Key_Semicolon:    ";",
    Qt.Key.Key_Apostrophe:   "'",
    Qt.Key.Key_Comma:        ",",
    Qt.Key.Key_Period:       ".",
    Qt.Key.Key_Slash:        "/",
}

_SPECIAL_MAP_MAC = {
    Qt.Key.Key_Escape:    "Esc",
    Qt.Key.Key_Tab:       "Tab",
    Qt.Key.Key_CapsLock:  "CapsLock",
    Qt.Key.Key_Return:    "Return",
    Qt.Key.Key_Backspace: "Delete",   # Mac "delete" key is Backspace keycode
    Qt.Key.Key_Space:     "Space",
    Qt.Key.Key_Control:   "Ctrl",     # ⌃ Control
    Qt.Key.Key_Alt:       "Option",   # ⌥ Option
    Qt.Key.Key_Shift:     "Shift",
    Qt.Key.Key_Meta:      "Cmd",      # ⌘ Command
    Qt.Key.Key_Left:      "←",
    Qt.Key.Key_Right:     "→",
    Qt.Key.Key_Up:        "↑",
    Qt.Key.Key_Down:      "↓",
    **{getattr(Qt.Key, f"Key_F{n}"): f"F{n}" for n in range(1, 13)},
    Qt.Key.Key_QuoteLeft:    "`",
    Qt.Key.Key_Minus:        "-",
    Qt.Key.Key_Equal:        "=",
    Qt.Key.Key_BracketLeft:  "[",
    Qt.Key.Key_BracketRight: "]",
    Qt.Key.Key_Backslash:    "\\",
    Qt.Key.Key_Semicolon:    ";",
    Qt.Key.Key_Apostrophe:   "'",
    Qt.Key.Key_Comma:        ",",
    Qt.Key.Key_Period:       ".",
    Qt.Key.Key_Slash:        "/",
}

_SPECIAL_MAP = _SPECIAL_MAP_MAC if _IS_MAC else _SPECIAL_MAP_WIN


class KeyWidget(QFrame):
    def __init__(self, key_label: str, parent=None):
        super().__init__(parent)
        self.key_label = key_label
        self._pressed  = False
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 4, 2, 4)
        self._lbl = QLabel(key_label)
        self._lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl.setStyleSheet("font-size: 10px; font-weight: 500;")
        layout.addWidget(self._lbl)
        self.setMinimumHeight(38)
        self.setMinimumWidth(52 if key_label in _WIDE else 34)
        self._apply(False)

    def _apply(self, pressed: bool):
        if pressed:
            self.setStyleSheet(
                "background:#4ade80;color:#0a1f0a;border-radius:5px;"
                "border:1px solid #22c55e;"
            )
        else:
            self.setStyleSheet(
                "background:rgba(255,255,255,0.05);color:inherit;"
                "border-radius:5px;border:1px solid rgba(255,255,255,0.12);"
            )

    def mark_pressed(self):
        if not self._pressed:
            self._pressed = True
            self._apply(True)

    def reset(self):
        self._pressed = False
        self._apply(False)


class KeyboardTestDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("input_key_test"))
        self.resize(860, 480)
        self._key_widgets: dict[str, KeyWidget] = {}
        self._tested = 0
        self._active = False
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        layout.addWidget(AppHeading("input_key_test", level=2))
        layout.addWidget(AppSecondaryLabel("input_press_keys"))

        kb_card = AppCard()
        for row in _KEY_LAYOUT:
            row_layout = QHBoxLayout()
            row_layout.setSpacing(4)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
            for k in row:
                kw = KeyWidget(k)
                # Duplicate keys (e.g., two Shift, two Cmd) get a suffix for the dict
                dict_key = k
                if dict_key in self._key_widgets:
                    dict_key = f"{k}_R"
                self._key_widgets[dict_key] = kw
                row_layout.addWidget(kw)
            row_layout.addStretch()
            kb_card.inner_layout().addLayout(row_layout)
        layout.addWidget(kb_card)

        bar = QHBoxLayout()
        self._progress_lbl = QLabel(f"0 / {len(self._key_widgets)} keys")
        _set_prop(self._progress_lbl, **{"app-text": "secondary"})
        self._start_btn = AppPrimaryButton(text=tr("input_start_test"))
        self._reset_btn = AppButton(text="Reset")
        self._start_btn.clicked.connect(self._toggle)
        self._reset_btn.clicked.connect(self._reset)
        bar.addWidget(self._progress_lbl)
        bar.addStretch()
        bar.addWidget(self._reset_btn)
        bar.addWidget(self._start_btn)
        layout.addLayout(bar)

    def _toggle(self):
        self._active = not self._active
        if self._active:
            self._start_btn.setText(f"⏹ {tr('stop')}")
            self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            self.setFocus()
        else:
            self._start_btn.setText(tr("input_start_test"))

    def _reset(self):
        for kw in self._key_widgets.values():
            kw.reset()
        self._tested = 0
        self._active = False
        self._start_btn.setText(tr("input_start_test"))
        self._progress_lbl.setText(f"0 / {len(self._key_widgets)} keys")

    def keyPressEvent(self, event: QKeyEvent):
        if not self._active:
            return
        matched = _SPECIAL_MAP.get(event.key())
        if not matched:
            matched = event.text().upper() if event.text().strip() else None
        if matched:
            # Try the primary key first, then the _R duplicate
            for candidate in (matched, f"{matched}_R"):
                if candidate in self._key_widgets and not self._key_widgets[candidate]._pressed:
                    self._key_widgets[candidate].mark_pressed()
                    self._tested += 1
                    self._progress_lbl.setText(f"{self._tested} / {len(self._key_widgets)} keys")
                    break
        event.accept()
