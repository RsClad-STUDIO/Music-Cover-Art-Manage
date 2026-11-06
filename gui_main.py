"""Compatibility entry point for the GUI application."""

import logging
import sys
import time
from pathlib import Path

STARTUP_STARTED = time.perf_counter()
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from PySide6.QtWidgets import QApplication
from music_cover_art_manage.gui import MainWindow

if __name__ == "__main__":
    qt_started = time.perf_counter()
    app = QApplication(sys.argv)
    qt_initialized = time.perf_counter()

    window = MainWindow()
    window_initialized = time.perf_counter()
    window.show()
    app.processEvents()
    first_paint_ready = time.perf_counter()

    logging.getLogger(__name__).info(
        "Startup timing: total=%.3fs; imports=%.3fs; QApplication=%.3fs; "
        "MainWindow=%.3fs; first display=%.3fs",
        first_paint_ready - STARTUP_STARTED,
        qt_started - STARTUP_STARTED,
        qt_initialized - qt_started,
        window_initialized - qt_initialized,
        first_paint_ready - window_initialized,
    )
    sys.exit(app.exec())
