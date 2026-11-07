import logging
import time

from PySide6.QtCore import QThread, Signal


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
        self.engine = None
        self._stop_requested = False

    def stop(self):
        self._stop_requested = True
        if self.engine is not None:
            self.engine.stop()

    def run(self):
        try:
            # Import the image-processing stack inside the worker thread so it
            # does not delay the GUI or block the first scan button click.
            from .core_engine import CoreEngine
            self.engine = CoreEngine(self.config, self.cache)
            if self._stop_requested:
                self.engine.stop()

            def report_progress(current, total, name):
                if name.startswith("SCAN_TARGET|"):
                    self.progress.emit(0, name)
                    return
                percentage = int(current / max(1, total) * 100)
                if name.startswith(("SUCCESS|", "SKIP|", "ERROR|")):
                    kind, filename = name.split("|", 1)
                    self.progress.emit(max(0, min(100, percentage)), f"{kind}|{current}/{total} | {filename}")
                else:
                    self.progress.emit(max(0, min(100, percentage)), f"{current}/{total} | {name}")

            if self.mode == "scan":
                result = self.engine.scan(
                    self.config.data["music_dir"], report_progress
                )
                cache_write_started = time.perf_counter()
                self.cache.update_entries(result.scanned_data)
                cache_write_seconds = time.perf_counter() - cache_write_started
                LOGGER.info(
                    "DB scan cache persistence: %.3fs; rows=%d",
                    cache_write_seconds,
                    len(result.scanned_data),
                )
                self.result_ready.emit(result)
            elif self.mode == "process":
                summary = self.engine.process(self.scan_result, report_progress)
                self.result_ready.emit(summary)
            else:
                raise ValueError(f"Unknown worker mode: {self.mode}")
        except Exception as exc:
            LOGGER.exception("Background %s task failed", self.mode)
            self.error_occurred.emit(str(exc))
