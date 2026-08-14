import os
import threading
import time
from pathlib import Path
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import processor
from optimizer import PerformanceOptimizer, PerfConfig

class ScanResult:
    def __init__(self):
        self.groups = defaultdict(list)
        self.stats = defaultdict(int)
        self.scanned_data = []
        self.dirty_images = {}

class CoreEngine:
    def __init__(self, config, cache):
        self.config = config
        self.cache = cache
        self.stop_event = threading.Event()
        self._lock = threading.Lock()
        self.processed_count = 0

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
            except: pass
        
        collect(music_dir)
        result.stats["total"] = len(all_files)
        
        def check(p, mt):
            if p in cache_map and cache_map[p][0] == mt:
                return p, mt, cache_map[p][1], False, None
            try:
                imgs = processor.get_images_info(Path(p))
                if not imgs: s, keep = "no_cover", None
                elif all(i.mime == processor.JPEG_MIME for i in imgs): s, keep = "already_jpeg", None
                else: s, keep = "dirty", imgs
            except Exception as e:
                s, keep = (str(e) if str(e).startswith("error:") else "error:unknown"), None
            return p, mt, s, True, keep

        workers = self.config.data.get("workers", 4)
        if not isinstance(workers, int): workers = 4
        
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = [ex.submit(check, p, mt) for p, mt in all_files]
            for i, f in enumerate(as_completed(futs)):
                if self.stop_event.is_set(): break
                p, mt, s, is_new, imgs = f.result()
                result.stats[s.split(':')[0]] += 1
                if s == "dirty":
                    result.groups[Path(p).parent].append(Path(p))
                    if imgs: result.dirty_images[Path(p)] = imgs
                if is_new: result.scanned_data.append((p, mt, s))
                progress_callback(i + 1, len(all_files), os.path.basename(p))
        return result

    def process(self, scan_result, progress_callback):
            self.stop_event.clear()
            total_dirty = scan_result.stats["dirty"]
            self.processed_count = 0
            
            music_dir = str(self.config.data["music_dir"])
            env_id = self._get_env_id(music_dir)
            
            # Auto モード判定
            is_auto = (self.config.data.get("workers") == "Auto" and 
                    self.config.data.get("sub_workers") == "Auto")
            
            optimizer = None
            if is_auto:
                # 過去データのロード
                opt_data = self.config.data.get("optimized_results", {}).get(env_id)
                optimizer = PerformanceOptimizer(env_id, opt_data)
                current_perf = optimizer.get_next_config()
            else:
                # 手動固定モード
                w = self.config.data.get("workers", 4)
                sw = self.config.data.get("sub_workers", 4)
                current_perf = PerfConfig(w, sw)
                print(f"[Core] Manual mode: {w}/{sw}")

            pending_albums = list(scan_result.groups.items())

            while pending_albums and not self.stop_event.is_set():
                if optimizer:
                    current_perf = optimizer.get_next_config()
                    optimizer.start_segment(current_perf)
                
                # セグメント実行 (10ファイル程度)
                segment_albums = []
                files_in_segment = 0
                while pending_albums and files_in_segment < 10:
                    album = pending_albums.pop(0)
                    segment_albums.append(album)
                    files_in_segment += len(album[1])

                with ThreadPoolExecutor(max_workers=current_perf.workers) as executor:
                    futs = [executor.submit(self._process_folder_internal, fld, fs, scan_result, current_perf.sub_workers, optimizer, progress_callback, total_dirty) 
                            for fld, fs in segment_albums]
                    for fut in as_completed(futs):
                        if self.stop_event.is_set(): break
                        self.cache.update_entries(fut.result())

                if optimizer:
                    optimizer.end_segment()

            # 最適化結果の保存
            if optimizer and not self.stop_event.is_set():
                if optimizer.save_result(self.config.data):
                    self.config.save()

    def _process_folder_internal(self, folder, files, scan_result, sub_workers, optimizer, progress_callback, total_dirty):
        folder_jpeg_cache = {}
        files_to_update = []
        for file_path in files:
            if self.stop_event.is_set(): break
            imgs = scan_result.dirty_images.get(file_path) or processor.get_images_info(file_path)
            try:
                for img in imgs:
                    if img.mime != processor.JPEG_MIME:
                        if img.hash not in folder_jpeg_cache:
                            folder_jpeg_cache[img.hash] = processor.to_jpeg_bytes(img.data, self.config.data["ffmpeg_path"])
                        img.data, img.mime = folder_jpeg_cache[img.hash], processor.JPEG_MIME
                files_to_update.append((file_path, imgs))
            except Exception:
                self._update_progress_atomic(progress_callback, total_dirty, file_path.name, optimizer)
                self.cache.set_entry(str(file_path), os.path.getmtime(file_path), "error:ffmpeg")

        results = []
        with ThreadPoolExecutor(max_workers=sub_workers) as sub_ex:
            def _upd(fp, ims):
                try:
                    processor.update_audio_images(fp, ims)
                    res = (str(fp), os.path.getmtime(fp), "ok")
                except Exception:
                    res = (str(fp), os.path.getmtime(fp), "error:unknown")
                self._update_progress_atomic(progress_callback, total_dirty, fp.name, optimizer)
                return res
            
            sub_futs = [sub_ex.submit(_upd, fp, ims) for fp, ims in files_to_update]
            for sf in as_completed(sub_futs): results.append(sf.result())
        return results

    def _update_progress_atomic(self, callback, total, name, optimizer):
        with self._lock:
            self.processed_count += 1
            if optimizer: optimizer.record_file()
            callback(self.processed_count, total, name)

    def _get_env_id(self, path):
        import platform
        is_unc = path.startswith('\\\\') or (len(path) > 1 and path[1] != ':')
        return f"{platform.node()}_{os.cpu_count()}_{'UNC' if is_unc else 'Local'}"