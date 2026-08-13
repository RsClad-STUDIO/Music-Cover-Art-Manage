from PySide6.QtCore import QThread, Signal
from core_engine import CoreEngine

class WorkerThread(QThread):
    progress = Signal(int, str)
    finished = Signal(object)

    def __init__(self, mode, config, cache, scan_result=None):
        super().__init__()
        self.mode, self.config, self.cache, self.scan_result = mode, config, cache, scan_result
        self.engine = CoreEngine(config, cache)

    def run(self):
        if self.mode == 'scan':
            def cb(c, t, n): self.progress.emit(int(c/t*100), n)
            res = self.engine.scan(self.config.data["music_dir"], cb)
            self.cache.update_entries(res.scanned_data)
            self.finished.emit(res)
        else:
            def cb(c, t, n): self.progress.emit(int(c/t*100), n)
            self.engine.process(self.scan_result, cb)
            self.finished.emit(None)
