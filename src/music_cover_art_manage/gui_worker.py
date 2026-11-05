import logging

from PySide6.QtCore import QThread, Signal

from .core_engine import CoreEngine

LOGGER = logging.getLogger(__name__)


class WorkerThread(QThread):
    progress = Signal(int, str)
    result_ready = Signal(object)
    error_occurred = Signal(str)

    def __init__(self, mode, config, cache, scan_result=None):
        super().__init__()
        self.mode = mode
        self.config = config
        self.cache = cache
        self.scan_result = scan_result
        self.engine = CoreEngine(config, cache)

    def stop(self):
        self.engine.stop()

    def run(self):
        try:
            def report_progress(current, total, name):
                percentage = int(current / max(1, total) * 100)
                self.progress.emit(max(0, min(100, percentage)), str(name))

            if self.mode == "scan":
                result = self.engine.scan(
                    self.config.data["music_dir"], report_progress
                )
                self.cache.update_entries(result.scanned_data)
                self.result_ready.emit(result)
            elif self.mode == "process":
                summary = self.engine.process(self.scan_result, report_progress)
                self.result_ready.emit(summary)
            else:
                raise ValueError(f"Unknown worker mode: {self.mode}")
        except Exception as exc:
            LOGGER.exception("Background %s task failed", self.mode)
            self.error_occurred.emit(str(exc))
