import os
import threading
from pathlib import Path
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import processor

class ScanResult:
    def __init__(self):
        self.groups = defaultdict(list)
        self.stats = defaultdict(int)
        self.scanned_data = []

class CoreEngine:
    def __init__(self, config, cache):
        self.config = config
        self.cache = cache
        self.stop_event = threading.Event()

    def scan(self, music_dir, progress_callback) -> ScanResult:
        self.stop_event.clear()
        result = ScanResult()
        cache_map = self.cache.load_all_to_dict()
        all_files = []
        def collect(d):
            try:
                with os.scandir(d) as it:
                    for e in it:
                        if self.stop_event.is_set(): break
                        if e.is_dir(): collect(e.path)
                        elif e.is_file() and os.path.splitext(e.name)[1].lower() in processor.SUPPORTED_EXTENSIONS:
                            all_files.append((e.path, e.stat().st_mtime))
            except Exception: pass
        collect(music_dir)
        result.stats["total"] = len(all_files)
        def check(p, mt):
            if p in cache_map and cache_map[p][0] == mt: return p, mt, cache_map[p][1], False
            try:
                imgs = processor.get_images_info(Path(p))
                if not imgs: s = "no_cover"
                elif all(i.mime == processor.JPEG_MIME for i in imgs): s = "already_jpeg"
                else: s = "dirty"
            except Exception as e: s = str(e) if str(e).startswith("error:") else "error:unknown"
            return p, mt, s, True
        with ThreadPoolExecutor(max_workers=self.config.data.get("workers", 8)) as ex:
            futures = [ex.submit(check, p, mt) for p, mt in all_files]
            for i, f in enumerate(futures):
                if self.stop_event.is_set(): break
                p, mt, s, is_new = f.result()
                result.stats[s.split(':')[0]] += 1
                if s == "dirty": result.groups[Path(p).parent].append(Path(p))
                if is_new: result.scanned_data.append((p, mt, s))
                progress_callback(i + 1, len(all_files), os.path.basename(p))
        return result

    def process(self, scan_result, progress_callback):
        self.stop_event.clear()
        total = scan_result.stats["dirty"]
        done = 0
        def _proc_fld(fld, fs):
            nonlocal done
            c, res = {}, []
            for p in fs:
                if self.stop_event.is_set(): break
                try:
                    imgs = processor.get_images_info(p)
                    for i in imgs:
                        if i.mime != processor.JPEG_MIME:
                            if i.hash not in c: c[i.hash] = processor.to_jpeg_bytes(i.data, self.config.data["ffmpeg_path"])
                            i.data, i.mime = c[i.hash], processor.JPEG_MIME
                    processor.update_audio_images(p, imgs)
                    s = "ok"
                except Exception as e: s = str(e) if str(e).startswith("error:") else "error:unknown"
                done += 1
                progress_callback(done, total, p.name)
                res.append((str(p), os.path.getmtime(p), s))
            return res
        with ThreadPoolExecutor(max_workers=self.config.data.get("workers", 8)) as ex:
            futs = [ex.submit(_proc_fld, fld, fs) for fld, fs in scan_result.groups.items()]
            for f in futs:
                if self.stop_event.is_set(): break
                self.cache.update_entries(f.result())
