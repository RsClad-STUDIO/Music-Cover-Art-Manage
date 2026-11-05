"""Compatibility entry point for the GUI application."""

import sys
from PySide6.QtWidgets import QApplication
from music_cover_art_manage.gui import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
