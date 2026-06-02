import json
from pathlib import Path
from functools import lru_cache

_THEMES_DIR = Path(__file__).parent.parent.parent / "assets" / "themes"
_cache: dict[str, dict] = {}
_current: dict = {}


def load_theme(name: str) -> dict:
    if name not in _cache:
        path = _THEMES_DIR / f"{name}.json"
        with open(path, encoding="utf-8") as f:
            _cache[name] = json.load(f)
    return _cache[name]


def apply_theme(name: str) -> dict:
    global _current
    _current = load_theme(name)
    return _current


def current() -> dict:
    return _current


def c(key: str) -> str:
    return _current.get("colors", {}).get(key, "#ff0000")


def build_stylesheet(theme: dict, font_size: int | None = None) -> str:
    t = theme
    co = t.get("colors", {})
    r = t.get("radius", 8)
    r_sm = t.get("radius_sm", 4)
    r_lg = t.get("radius_lg", 12)
    ff = t.get("font_family", "Segoe UI")
    fs = font_size or t.get("font_size", 13)

    def clr(k):
        return co.get(k, "#888888")

    return f"""
/* ── Global ───────────────────────────────────────────── */
QWidget {{
    font-family: "{ff}";
    font-size: {fs}px;
    color: {clr("text_primary")};
    background: transparent;
    border: none;
    outline: none;
}}

QMainWindow, QDialog {{
    background: {clr("bg_window")};
}}

/* ── Scroll Bars ──────────────────────────────────────── */
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {clr("scrollbar")};
    border-radius: 3px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {clr("scrollbar_hover")};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 6px;
}}
QScrollBar::handle:horizontal {{
    background: {clr("scrollbar")};
    border-radius: 3px;
    min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {clr("scrollbar_hover")};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ── App-specific classes (via setProperty / setObjectName) ── */

/* Cards */
QFrame[app-card="true"] {{
    background: {clr("bg_card")};
    border: 1px solid {clr("border")};
    border-radius: {r}px;
}}
QFrame[app-card="true"]:hover {{
    border-color: {clr("accent")};
}}

/* Sidebar */
QFrame#sidebar {{
    background: {clr("bg_sidebar")};
    border-right: 1px solid {clr("border")};
}}

/* Sidebar nav buttons */
QPushButton[app-nav="true"] {{
    background: transparent;
    color: {clr("text_secondary")};
    border: none;
    border-radius: {r}px;
    padding: 10px 14px;
    text-align: left;
    font-size: {fs}px;
}}
QPushButton[app-nav="true"]:hover {{
    background: {clr("bg_hover")};
    color: {clr("text_primary")};
}}
QPushButton[app-nav="true"][active="true"] {{
    background: {clr("bg_hover")};
    color: {clr("accent")};
    font-weight: bold;
}}

/* Primary button */
QPushButton[app-btn="primary"] {{
    background: {clr("accent")};
    color: {clr("text_on_accent")};
    border: none;
    border-radius: {r}px;
    padding: 10px 20px;
    font-weight: 600;
    font-size: {fs}px;
}}
QPushButton[app-btn="primary"]:hover {{
    background: {clr("accent_hover")};
}}
QPushButton[app-btn="primary"]:pressed {{
    background: {clr("accent")};
    opacity: 0.8;
}}
QPushButton[app-btn="primary"]:disabled {{
    background: {clr("bg_hover")};
    color: {clr("text_muted")};
}}

/* Secondary button */
QPushButton[app-btn="secondary"] {{
    background: {clr("bg_hover")};
    color: {clr("text_primary")};
    border: 1px solid {clr("border")};
    border-radius: {r}px;
    padding: 9px 18px;
    font-size: {fs}px;
}}
QPushButton[app-btn="secondary"]:hover {{
    background: {clr("bg_pressed")};
    border-color: {clr("accent")};
}}
QPushButton[app-btn="secondary"]:pressed {{
    background: {clr("bg_pressed")};
}}

/* Ghost button */
QPushButton[app-btn="ghost"] {{
    background: transparent;
    color: {clr("accent")};
    border: none;
    border-radius: {r}px;
    padding: 8px 14px;
    font-size: {fs}px;
}}
QPushButton[app-btn="ghost"]:hover {{
    background: {clr("bg_hover")};
}}

/* Icon button */
QPushButton[app-btn="icon"] {{
    background: transparent;
    border: none;
    border-radius: {r}px;
    padding: 4px;
    font-size: 18px;
    color: {clr("text_secondary")};
}}
QPushButton[app-btn="icon"]:hover {{
    background: {clr("bg_hover")};
    color: {clr("text_primary")};
}}

/* Inputs */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background: {clr("bg_input")};
    color: {clr("text_primary")};
    border: 1px solid {clr("border")};
    border-radius: {r_sm}px;
    padding: 8px 12px;
    selection-background-color: {clr("accent")};
}}
QLineEdit:focus, QTextEdit:focus {{
    border-color: {clr("border_focus")};
}}

/* SpinBox */
QSpinBox {{
    background: {clr("bg_input")};
    color: {clr("text_primary")};
    border: 1px solid {clr("border")};
    border-radius: {r_sm}px;
    padding: 6px 8px 6px 10px;
    min-width: 90px;
}}
QSpinBox:focus {{
    border-color: {clr("border_focus")};
}}
QSpinBox::up-button, QSpinBox::down-button {{
    width: 22px;
    background: {clr("bg_hover")};
    border-left: 1px solid {clr("border")};
}}
QSpinBox::up-button {{
    subcontrol-origin: border;
    subcontrol-position: top right;
    border-top-right-radius: {r_sm}px;
    border-bottom: 1px solid {clr("border")};
}}
QSpinBox::down-button {{
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    border-bottom-right-radius: {r_sm}px;
}}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
    background: {clr("bg_pressed")};
}}
QSpinBox::up-arrow {{
    width: 0; height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-bottom: 5px solid {clr("text_secondary")};
}}
QSpinBox::down-arrow {{
    width: 0; height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {clr("text_secondary")};
}}

/* ComboBox */
QComboBox {{
    background: {clr("bg_input")};
    color: {clr("text_primary")};
    border: 1px solid {clr("border")};
    border-radius: {r_sm}px;
    padding: 7px 12px;
    min-height: 36px;
}}
QComboBox:focus {{
    border-color: {clr("border_focus")};
}}
QComboBox::drop-down {{
    border: none;
    width: 28px;
}}
QComboBox::down-arrow {{
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid {clr("text_secondary")};
    width: 0;
    height: 0;
}}
QComboBox QAbstractItemView {{
    background: {clr("bg_card")};
    color: {clr("text_primary")};
    border: 1px solid {clr("border")};
    border-radius: {r_sm}px;
    selection-background-color: {clr("accent")};
    outline: none;
}}

/* Labels */
QLabel[app-heading="h1"] {{
    font-size: {fs + 8}px;
    font-weight: 700;
    color: {clr("text_primary")};
}}
QLabel[app-heading="h2"] {{
    font-size: {fs + 4}px;
    font-weight: 600;
    color: {clr("text_primary")};
}}
QLabel[app-heading="h3"] {{
    font-size: {fs + 2}px;
    font-weight: 600;
    color: {clr("text_primary")};
}}
QLabel[app-text="secondary"] {{
    color: {clr("text_secondary")};
}}
QLabel[app-text="muted"] {{
    color: {clr("text_muted")};
    font-size: {fs - 1}px;
}}
QLabel[app-text="accent"] {{
    color: {clr("accent")};
    font-weight: 600;
}}

/* Status badges */
QLabel[app-badge="pass"] {{
    background: {clr("status_pass_bg")};
    color: {clr("status_pass")};
    border-radius: {r_sm}px;
    padding: 3px 10px;
    font-weight: 600;
    font-size: {fs - 1}px;
}}
QLabel[app-badge="warn"] {{
    background: {clr("status_warn_bg")};
    color: {clr("status_warn")};
    border-radius: {r_sm}px;
    padding: 3px 10px;
    font-weight: 600;
    font-size: {fs - 1}px;
}}
QLabel[app-badge="fail"] {{
    background: {clr("status_fail_bg")};
    color: {clr("status_fail")};
    border-radius: {r_sm}px;
    padding: 3px 10px;
    font-weight: 600;
    font-size: {fs - 1}px;
}}
QLabel[app-badge="info"] {{
    background: {clr("status_info_bg")};
    color: {clr("status_info")};
    border-radius: {r_sm}px;
    padding: 3px 10px;
    font-weight: 600;
    font-size: {fs - 1}px;
}}

/* Progress bar */
QProgressBar {{
    background: {clr("bg_input")};
    border: none;
    border-radius: {r_sm}px;
    height: 6px;
    text-align: center;
}}
QProgressBar::chunk {{
    background: {clr("accent")};
    border-radius: {r_sm}px;
}}
QProgressBar[status="pass"]::chunk {{
    background: {clr("status_pass")};
}}
QProgressBar[status="warn"]::chunk {{
    background: {clr("status_warn")};
}}
QProgressBar[status="fail"]::chunk {{
    background: {clr("status_fail")};
}}

/* CheckBox */
QCheckBox {{
    spacing: 8px;
    color: {clr("text_primary")};
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 2px solid {clr("border")};
    border-radius: {r_sm}px;
    background: {clr("bg_input")};
}}
QCheckBox::indicator:checked {{
    background: {clr("accent")};
    border-color: {clr("accent")};
}}

/* Tooltip */
QToolTip {{
    background: {clr("bg_card")};
    color: {clr("text_primary")};
    border: 1px solid {clr("border")};
    border-radius: {r_sm}px;
    padding: 6px 10px;
}}

/* Tab widget */
QTabWidget::pane {{
    border: none;
    background: transparent;
}}
QTabBar::tab {{
    background: transparent;
    color: {clr("text_secondary")};
    padding: 10px 18px;
    border-bottom: 2px solid transparent;
    font-size: {fs}px;
}}
QTabBar::tab:selected {{
    color: {clr("accent")};
    border-bottom-color: {clr("accent")};
    font-weight: 600;
}}
QTabBar::tab:hover:!selected {{
    color: {clr("text_primary")};
}}

/* Separator */
QFrame[app-sep="true"] {{
    background: {clr("separator")};
    border: none;
    max-height: 1px;
    min-height: 1px;
}}
"""
