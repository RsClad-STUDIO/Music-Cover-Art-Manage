import ctypes
import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QPlainTextEdit, QProgressBar, QPushButton,
    QVBoxLayout, QWidget,
)

from cache_manager import Cache
from config_manager import Config, resolve_ffmpeg_path
from gui_worker import WorkerThread
import gui_style

if sys.platform == "win32":
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
        "MusicCoverArtManage"
    )


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = Config()
        resolved_ffmpeg = resolve_ffmpeg_path(self.config.data.get("ffmpeg_path"))
        if os.path.isfile(resolved_ffmpeg):
            self.config.data["ffmpeg_path"] = resolved_ffmpeg
        self.cache = Cache()
        self.is_dark = True
        self.scan_results = None
        self.worker = None
        self.worker_mode = None
        self.last_process_stats = None
        self.init_ui()
        self.apply_theme()

    def init_ui(self):
        self.setWindowTitle("Music Cover Art Manage")
        self.resize(900, 700)
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        header = QHBoxLayout()
        title = QLabel("Cover Art Optimizer")
        header.addWidget(title)
        self.theme_btn = QPushButton("Theme")
        self.theme_btn.clicked.connect(self.toggle_theme)
        header.addWidget(self.theme_btn, 0, Qt.AlignmentFlag.AlignRight)
        layout.addLayout(header)

        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        self.dir_edit = QLineEdit(self.config.data["music_dir"])
        self.dir_edit.setPlaceholderText(r"Example: C:\Music or Y:\Music")
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self.browse_music_dir)
        self.ff_edit = QLineEdit(self.config.data["ffmpeg_path"])
        self.ff_edit.setPlaceholderText("Bundled FFmpeg is detected automatically")
        music_row = QHBoxLayout()
        music_row.addWidget(QLabel("Music Dir:"))
        music_row.addWidget(self.dir_edit)
        music_row.addWidget(self.browse_btn)
        card_layout.addLayout(music_row)
        ffmpeg_row = QHBoxLayout()
        ffmpeg_row.addWidget(QLabel("FFmpeg:"))
        ffmpeg_row.addWidget(self.ff_edit)
        card_layout.addLayout(ffmpeg_row)
        layout.addWidget(card)

        button_layout = QHBoxLayout()
        self.scan_btn = QPushButton("Scan Library")
        self.scan_btn.clicked.connect(self.start_scan)
        self.start_btn = QPushButton("Start Conversion")
        self.start_btn.setEnabled(False)
        self.start_btn.clicked.connect(self.start_conversion)
        button_layout.addWidget(self.scan_btn)
        button_layout.addWidget(self.start_btn)
        layout.addLayout(button_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)
        self.log_area = QPlainTextEdit()
        self.log_area.setReadOnly(True)
        layout.addWidget(self.log_area)

    def browse_music_dir(self):
        selected = QFileDialog.getExistingDirectory(
            self, "Select music folder", self.dir_edit.text().strip().strip('"')
        )
        if selected:
            self.dir_edit.setText(selected)

    def apply_theme(self):
        self.setStyleSheet(gui_style.get_stylesheet(self.is_dark))

    def toggle_theme(self):
        self.is_dark = not self.is_dark
        self.apply_theme()

    def _connect_worker(self, worker):
        worker.progress.connect(self.update_progress)
        worker.result_ready.connect(self.on_worker_result)
        worker.error_occurred.connect(self.on_worker_error)
        worker.finished.connect(self.on_worker_stopped)
        self.worker = worker
        self.worker_mode = worker.mode
        worker.start()

    def start_scan(self):
        music_dir = self.dir_edit.text().strip().strip('"')
        if not music_dir or not os.path.isdir(music_dir):
            QMessageBox.warning(self, "Invalid folder", "Select an existing music folder.")
            self.dir_edit.setFocus()
            return

        self.config.data["music_dir"] = music_dir
        self.config.data["ffmpeg_path"] = self.ff_edit.text().strip().strip('"')
        self.config.save()
        self.scan_results = None
        self.last_process_stats = None
        self.progress_bar.setValue(0)
        self.log_area.clear()
        self.scan_btn.setEnabled(False)
        self.start_btn.setEnabled(False)
        self.status_label.setText("Scanning library...")
        self._connect_worker(WorkerThread("scan", self.config, self.cache))

    def start_conversion(self):
        if self.scan_results is None:
            return
        self.config.data["ffmpeg_path"] = self.ff_edit.text().strip().strip('"')
        self.config.save()
        self.last_process_stats = None
        self.progress_bar.setValue(0)
        self.start_btn.setEnabled(False)
        self.scan_btn.setEnabled(False)
        self.status_label.setText("Converting cover art...")
        self._connect_worker(
            WorkerThread("process", self.config, self.cache, self.scan_results)
        )

    def on_worker_result(self, result):
        if hasattr(result, "stats") and hasattr(result, "dirty_images"):
            self.scan_results = result
            stats = result.stats
            self.log_area.appendPlainText(
                "Scan Complete\\n"
                f"Total: {stats['total']} | Dirty: {stats['dirty']} | "
                f"Already JPEG: {stats['already_jpeg']} | "
                f"No Cover: {stats['no_cover']} | Errors: {stats['error']}"
            )
            self.start_btn.setEnabled(stats["dirty"] > 0)
            self.status_label.setText("Scan completed")
            self.progress_bar.setValue(100)
        elif isinstance(result, dict):
            self.last_process_stats = result
            self.log_area.appendPlainText(
                "Conversion Complete\\n"
                f"Success: {result.get('success', 0)} | "
                f"Errors: {result.get('error', 0)} | "
                f"Skipped: {result.get('skipped', 0)}"
            )
            if result.get("error", 0):
                self.status_label.setText("Completed with errors")
                self.start_btn.setEnabled(True)
            else:
                self.status_label.setText("Conversion completed")
                self.start_btn.setEnabled(False)
            self.progress_bar.setValue(100)

    def on_worker_error(self, message):
        if self.worker_mode == "process":
            self.last_process_stats = {"success": 0, "error": 1, "skipped": 0}
        self.status_label.setText("Operation failed")
        self.log_area.appendPlainText(f"Error: {message}")
        QMessageBox.critical(self, "Operation failed", message)

    def on_worker_stopped(self):
        self.scan_btn.setEnabled(True)
        if self.worker_mode == "scan":
            self.start_btn.setEnabled(
                self.scan_results is not None
                and self.scan_results.stats.get("dirty", 0) > 0
            )
        else:
            self.start_btn.setEnabled(
                bool(self.last_process_stats and self.last_process_stats.get("error", 0))
            )
        self.worker = None
        self.worker_mode = None

    def update_progress(self, value, name):
        self.progress_bar.setValue(value)
        self.status_label.setText(f"Processing: {name}")

    def closeEvent(self, event):
        if self.worker is not None and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
        self.cache.close()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    if getattr(sys, "frozen", False):
        icon_path = os.path.join(sys._MEIPASS, "icon.ico")
    else:
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
    if os.path.isfile(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
