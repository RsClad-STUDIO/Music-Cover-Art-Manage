import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit, QFileDialog, QProgressBar, QPlainTextEdit, QFrame)
from PySide6.QtCore import Qt
from config_manager import Config
from cache_manager import Cache
from gui_worker import WorkerThread
import gui_style
from PySide6.QtGui import QIcon
import ctypes
import os

if sys.platform == "win32":
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
        "MusicCoverArtManage"
    )

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config, self.cache = Config(), Cache()
        self.is_dark, self.scan_results = True, None
        self.init_ui()
        self.apply_theme()

    def init_ui(self):
        self.setWindowTitle("Music Cover Art Manage")
        self.resize(900, 700)
        central = QWidget(); self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        header = QHBoxLayout()
        title = QLabel("Cover Art Optimizer")
        header.addWidget(title)
        self.theme_btn = QPushButton("Theme"); self.theme_btn.clicked.connect(self.toggle_theme)
        header.addWidget(self.theme_btn, 0, Qt.AlignRight)
        layout.addLayout(header)

        card = QFrame(); card.setObjectName("Card"); card_layout = QVBoxLayout(card)
        self.dir_edit = QLineEdit(self.config.data["music_dir"])
        self.ff_edit = QLineEdit(self.config.data["ffmpeg_path"])
        for label, edit in [("Music Dir:", self.dir_edit), ("FFmpeg:", self.ff_edit)]:
            row = QHBoxLayout(); row.addWidget(QLabel(label)); row.addWidget(edit)
            card_layout.addLayout(row)
        layout.addWidget(card)

        btn_layout = QHBoxLayout()
        self.scan_btn = QPushButton("Scan Library"); self.scan_btn.clicked.connect(self.start_scan)
        self.start_btn = QPushButton("Start Conversion"); self.start_btn.setEnabled(False); self.start_btn.clicked.connect(self.start_conversion)
        btn_layout.addWidget(self.scan_btn); btn_layout.addWidget(self.start_btn)
        layout.addLayout(btn_layout)

        self.progress_bar = QProgressBar(); layout.addWidget(self.progress_bar)
        self.status_label = QLabel("Ready"); layout.addWidget(self.status_label)
        self.log_area = QPlainTextEdit(); self.log_area.setReadOnly(True); layout.addWidget(self.log_area)

    def apply_theme(self): self.setStyleSheet(gui_style.get_stylesheet(self.is_dark))
    def toggle_theme(self): self.is_dark = not self.is_dark; self.apply_theme()
    def start_scan(self):
        self.config.data["music_dir"], self.config.data["ffmpeg_path"] = self.dir_edit.text(), self.ff_edit.text()
        self.config.save(); self.log_area.clear(); self.scan_btn.setEnabled(False)
        self.worker = WorkerThread('scan', self.config, self.cache)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.on_scan_finished)
        self.worker.start()

    def on_scan_finished(self, res):
        self.scan_results = res; self.scan_btn.setEnabled(True)
        s = res.stats
        self.log_area.appendPlainText(f"Scan Complete\nTotal: {s['total']} | Dirty: {s['dirty']} | Already JPEG: {s['already_jpeg']}")
        if s['dirty'] > 0: self.start_btn.setEnabled(True)

    def start_conversion(self):
        self.start_btn.setEnabled(False)
        self.worker = WorkerThread('process', self.config, self.cache, self.scan_results)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(lambda _: self.status_label.setText("Finished"))
        self.worker.start()

    def update_progress(self, val, name):
        self.progress_bar.setValue(val); self.status_label.setText(f"Processing: {name}")

if sys.platform == "win32":
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
        "MusicCoverArtManage"
    )

if __name__ == "__main__":
    app = QApplication(sys.argv)

    if getattr(sys, "frozen", False):
        icon_path = os.path.join(sys._MEIPASS, "icon.ico")
    else:
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")

    app.setWindowIcon(QIcon(icon_path))

    window = MainWindow()
    window.show()
    sys.exit(app.exec())