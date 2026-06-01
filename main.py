import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QSharedMemory
from PyQt6.QtGui import QFont

from app.core.settings import settings
from app.core.translator import set_language
from app.core import theme as theme_module


def _already_running(app: QApplication) -> bool:
    """Return True if another instance is already running."""
    mem = QSharedMemory("LapTest_SingleInstance_v1")
    if mem.attach():
        mem.detach()
        return True
    if not mem.create(1):
        return True
    app._shared_mem = mem   # keep alive for the process lifetime
    return False


def main():
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    os.environ.setdefault("QT_SCALE_FACTOR_ROUNDING_POLICY", "PassThrough")

    app = QApplication(sys.argv)
    app.setApplicationName("LapTest")
    app.setOrganizationName("LapTest")
    app.setApplicationVersion("0.1.0")

    if _already_running(app):
        QMessageBox.information(None, "LapTest", "LapTest is already running.")
        sys.exit(0)

    set_language(settings.language)
    t = theme_module.apply_theme(settings.theme)

    font = QFont(t.get("font_family", "Segoe UI"), t.get("font_size", 13))
    app.setFont(font)

    from app.ui.main_window import MainWindow
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
