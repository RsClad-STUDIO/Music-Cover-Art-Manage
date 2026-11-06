import ctypes
import os
import sys
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit, QProgressBar, QPushButton, QVBoxLayout, QWidget
from .cache_manager import Cache
from .config_manager import Config, resolve_ffmpeg_path
from .gui_worker import WorkerThread
from . import gui_style

if sys.platform == "win32":
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("MusicCoverArtManage")

def icon_path():
    root = sys._MEIPASS if getattr(sys, "frozen", False) else os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(root, "assets", "icon.ico")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = Config()
        ff = resolve_ffmpeg_path(self.config.data.get("ffmpeg_path"))
        if os.path.isfile(ff):
            self.config.data["ffmpeg_path"] = ff
        self.cache = Cache()
        self.scan_results = self.worker = self.worker_mode = self.last_process_stats = None
        self.theme_mode = "auto"
        self.init_ui()
        QApplication.instance().styleHints().colorSchemeChanged.connect(self.apply_theme)
        self.apply_theme()

    def init_ui(self):
        self.setWindowTitle("Music Cover Art Manage")
        self.setWindowIcon(QIcon(icon_path()))
        self.resize(1000, 760)
        self.setMinimumSize(760, 600)
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(24, 22, 24, 20)
        root.setSpacing(15)
        head = QHBoxLayout()
        titles = QVBoxLayout()
        title = QLabel("Music Cover Art Manage")
        title.setObjectName("PageTitle")
        subtitle = QLabel("音楽ライブラリのカバーアートをスキャン・最適化")
        subtitle.setObjectName("Muted")
        titles.addWidget(title)
        titles.addWidget(subtitle)
        head.addLayout(titles)
        head.addStretch()
        self.theme_btn = QPushButton("テーマ: 自動")
        self.theme_btn.clicked.connect(self.cycle_theme)
        head.addWidget(self.theme_btn)
        root.addLayout(head)

        panel = QFrame()
        panel.setObjectName("Panel")
        form = QVBoxLayout(panel)
        form.setContentsMargins(18, 16, 18, 16)
        form.setSpacing(12)
        section = QLabel("ライブラリ設定")
        section.setObjectName("SectionTitle")
        form.addWidget(section)
        row = QHBoxLayout()
        row.addWidget(QLabel("音楽フォルダー"))
        self.dir_edit = QLineEdit(self.config.data["music_dir"])
        self.dir_edit.setPlaceholderText(r"例: C:\Music または Y:\Music")
        self.browse_btn = QPushButton("参照…")
        self.browse_btn.clicked.connect(self.browse_music_dir)
        row.addWidget(self.dir_edit, 1)
        row.addWidget(self.browse_btn)
        form.addLayout(row)
        row = QHBoxLayout()
        row.addWidget(QLabel("FFmpeg"))
        self.ff_edit = QLineEdit(self.config.data["ffmpeg_path"])
        self.ff_edit.setPlaceholderText("FFmpeg実行ファイルのパス")
        row.addWidget(self.ff_edit, 1)
        form.addLayout(row)
        root.addWidget(panel)

        actions = QHBoxLayout()
        self.scan_btn = QPushButton("ライブラリをスキャン")
        self.scan_btn.clicked.connect(self.start_scan)
        self.start_btn = QPushButton("最適化を開始")
        self.start_btn.setObjectName("Primary")
        self.start_btn.setEnabled(False)
        self.start_btn.clicked.connect(self.start_conversion)
        actions.addWidget(self.scan_btn)
        actions.addWidget(self.start_btn)
        actions.addStretch()
        root.addLayout(actions)

        progress = QFrame()
        progress.setObjectName("Panel")
        pl = QVBoxLayout(progress)
        pl.setContentsMargins(18, 13, 18, 13)
        self.status_label = QLabel("準備完了")
        self.status_label.setObjectName("SectionTitle")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        pl.addWidget(self.status_label)
        pl.addWidget(self.progress_bar)
        root.addWidget(progress)

        loghead = QHBoxLayout()
        logtitle = QLabel("処理ログ")
        logtitle.setObjectName("SectionTitle")
        loghead.addWidget(logtitle)
        loghead.addStretch()
        clear = QPushButton("ログをクリア")
        clear.clicked.connect(self.log_area_clear)
        loghead.addWidget(clear)
        root.addLayout(loghead)
        self.log_area = QPlainTextEdit()
        self.log_area.setObjectName("Log")
        self.log_area.setReadOnly(True)
        self.log_area.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.log_area.setPlaceholderText("処理の進行状況と結果がここに表示されます。")
        root.addWidget(self.log_area, 1)

    def apply_theme(self, *_):
        if self.theme_mode == "auto":
            self.is_dark = QApplication.instance().styleHints().colorScheme() == Qt.ColorScheme.Dark
        else:
            self.is_dark = self.theme_mode == "dark"
        self.setStyleSheet(gui_style.get_stylesheet(self.is_dark))
        self.theme_btn.setText({"auto": "テーマ: 自動", "dark": "テーマ: ダーク", "light": "テーマ: ライト"}[self.theme_mode])

    def cycle_theme(self):
        self.theme_mode = {"auto": "dark", "dark": "light", "light": "auto"}[self.theme_mode]
        self.apply_theme()

    def log_area_clear(self):
        self.log_area.clear()

    def browse_music_dir(self):
        path = QFileDialog.getExistingDirectory(self, "音楽フォルダーを選択", self.dir_edit.text().strip().strip('"'))
        if path:
            self.dir_edit.setText(path)

    def _connect_worker(self, worker):
        worker.progress.connect(self.update_progress)
        worker.result_ready.connect(self.on_worker_result)
        worker.error_occurred.connect(self.on_worker_error)
        worker.finished.connect(self.on_worker_stopped)
        self.worker, self.worker_mode = worker, worker.mode
        worker.start()

    def start_scan(self):
        folder = self.dir_edit.text().strip().strip('"')
        if not folder or not os.path.isdir(folder):
            QMessageBox.warning(self, "フォルダーが無効です", "存在する音楽フォルダーを選択してください。")
            self.dir_edit.setFocus()
            return
        self.config.data["music_dir"] = folder
        self.config.data["ffmpeg_path"] = self.ff_edit.text().strip().strip('"')
        self.config.save()
        self.scan_results = self.last_process_stats = None
        self.progress_bar.setValue(0)
        self.log_area.clear()
        self.scan_btn.setEnabled(False)
        self.start_btn.setEnabled(False)
        self.status_label.setText("ライブラリをスキャンしています…")
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
        self.status_label.setText("カバーアートを最適化しています…")
        self._connect_worker(WorkerThread("process", self.config, self.cache, self.scan_results))

    def on_worker_result(self, result):
        if hasattr(result, "stats") and hasattr(result, "dirty_images"):
            self.scan_results = result
            s = result.stats
            self.log_area.appendPlainText(f"スキャン完了\n対象: {s['total']} | 要最適化: {s['dirty']} | JPEG済み: {s['already_jpeg']} | カバーなし: {s['no_cover']} | エラー: {s['error']}")
            if result.cancelled:
                self.start_btn.setEnabled(False)
                self.status_label.setText("スキャンはキャンセルされました")
                self.log_area.appendPlainText("スキャンは完了前にキャンセルされました。")
            else:
                self.start_btn.setEnabled(s["dirty"] > 0)
                self.status_label.setText("スキャン完了")
            self.progress_bar.setValue(100)
        elif isinstance(result, dict):
            self.last_process_stats = result
            self.log_area.appendPlainText(f"最適化完了\n成功: {result.get('success', 0)} | エラー: {result.get('error', 0)} | スキップ: {result.get('skipped', 0)}")
            if result.get("cancelled"):
                self.status_label.setText("最適化はキャンセルされました")
                self.start_btn.setEnabled(True)
            elif result.get("error", 0):
                self.status_label.setText("エラーを含めて完了")
                self.start_btn.setEnabled(True)
            else:
                self.status_label.setText("最適化完了")
                self.start_btn.setEnabled(False)
            self.progress_bar.setValue(100)

    def on_worker_error(self, message):
        if self.worker_mode == "process":
            self.last_process_stats = {"success": 0, "error": 1, "skipped": 0}
        self.status_label.setText("処理に失敗しました")
        self.log_area.appendPlainText(f"エラー: {message}")
        QMessageBox.critical(self, "処理に失敗しました", message)

    def on_worker_stopped(self):
        self.scan_btn.setEnabled(True)
        if self.worker_mode == "scan":
            self.start_btn.setEnabled(self.scan_results is not None and not self.scan_results.cancelled and self.scan_results.stats.get("dirty", 0) > 0)
        else:
            self.start_btn.setEnabled(bool(self.last_process_stats and (self.last_process_stats.get("error", 0) or self.last_process_stats.get("cancelled", False))))
        self.worker = self.worker_mode = None

    def update_progress(self, value, name):
        self.progress_bar.setValue(value)
        self.status_label.setText(f"処理中: {name}")

    def closeEvent(self, event):
        if self.worker is not None and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
        self.cache.close()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(icon_path()))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
