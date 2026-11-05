import logging
import os
import platform
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path, PureWindowsPath

import processor
from config_manager import resolve_ffmpeg_path
from optimizer import PerformanceOptimizer, PerfConfig

LOGGER = logging.getLogger(__name__)
MIN_WORKERS = 1
MAX_WORKERS = 32


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

    @staticmethod
    def _worker_count(value, default=4):
        try:
            count = int(value)
        except (TypeError, ValueError):
            count = default
        return max(MIN_WORKERS, min(MAX_WORKERS, count))

    def scan(self, music_dir, progress_callback=None) -> ScanResult:
        self.stop_event.clear()
        result = ScanResult()
        cache_map = self.cache.load_all_to_dict()
        all_files = []
        root = Path(str(music_dir).strip().strip('"'))
        if not root.is_dir():
            result.stats["error"] += 1
            LOGGER.error("Scan directory does not exist or is not accessible: %s", root)
            return result

        # Iterative traversal avoids recursion-depth failures and does not follow
        # directory symlinks, preventing accidental loops.
        pending_dirs = [root]
        while pending_dirs and not self.stop_event.is_set():
            directory = pending_dirs.pop()
            try:
                with os.scandir(directory) as entries:
                    for entry in entries:
                        if self.stop_event.is_set():
                            break
                        try:
                            if entry.is_dir(follow_symlinks=False):
                                pending_dirs.append(Path(entry.path))
                            elif (
                                entry.is_file(follow_symlinks=False)
                                and Path(entry.name).suffix.lower() in processor.SUPPORTED_EXTENSIONS
                            ):
                                all_files.append((Path(entry.path), entry.stat(follow_symlinks=False).st_mtime))
                        except OSError as exc:
                            result.stats["error"] += 1
                            LOGGER.warning("Could not inspect %s: %s", entry.path, exc)
            except OSError as exc:
                result.stats["error"] += 1
                LOGGER.warning("Could not scan directory %s: %s", directory, exc)

        result.stats["total"] = len(all_files)

        def check(path, mtime):
            cache_entry = cache_map.get(str(path))
            if cache_entry and cache_entry[0] == mtime:
                cached_status = str(cache_entry[1])
                # A cached 'dirty' item must be re-read to rebuild the artwork
                # payload. Error states are retried so transient failures recover.
                if cached_status in {"ok", "no_cover", "already_jpeg"}:
                    return path, mtime, cached_status, False, None
            try:
                images = processor.get_images_info(path)
                if not images:
                    status, keep = "no_cover", None
                elif all(image.mime == processor.JPEG_MIME for image in images):
                    status, keep = "already_jpeg", None
                else:
                    status, keep = "dirty", images
            except Exception as exc:
                message = str(exc)
                status = message if message.startswith("error:") else f"error:unknown:{message}"
                keep = None
            return path, mtime, status, True, keep

        configured_workers = self.config.data.get("workers", 4)
        workers = self._worker_count(configured_workers, 4)
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="cover-scan") as executor:
            futures = [executor.submit(check, path, mtime) for path, mtime in all_files]
            for index, future in enumerate(as_completed(futures), start=1):
                if self.stop_event.is_set():
                    for pending in futures:
                        pending.cancel()
                    break
                try:
                    path, mtime, status, is_new, images = future.result()
                except Exception as exc:
                    result.stats["error"] += 1
                    LOGGER.exception("Unexpected scan worker failure: %s", exc)
                    continue

                result.stats[status.split(":", 1)[0]] += 1
                if status == "dirty":
                    result.groups[path.parent].append(path)
                    result.dirty_images[path] = images or []
                if is_new:
                    result.scanned_data.append((str(path), mtime, status))
                if progress_callback:
                    try:
                        progress_callback(index, len(all_files), path.name)
                    except Exception:
                        LOGGER.exception("Scan progress callback failed")

        return result

    def process(self, scan_result, progress_callback=None):
        self.stop_event.clear()
        total_dirty = int(scan_result.stats.get("dirty", 0))
        self.processed_count = 0
        if total_dirty == 0:
            return

        music_dir = str(self.config.data.get("music_dir", ""))
        env_id = self._get_env_id(music_dir)
        is_auto = (
            self.config.data.get("workers") == "Auto"
            and self.config.data.get("sub_workers") == "Auto"
        )

        optimizer = None
        if is_auto:
            opt_data = self.config.data.get("optimized_results", {}).get(env_id)
            optimizer = PerformanceOptimizer(env_id, opt_data)
        else:
            workers = self._worker_count(self.config.data.get("workers", 4), 4)
            sub_workers = self._worker_count(self.config.data.get("sub_workers", 4), 4)
            current_perf = PerfConfig(workers, sub_workers)
            LOGGER.info("Manual processing mode: %s/%s", workers, sub_workers)

        pending_albums = list(scan_result.groups.items())
        while pending_albums and not self.stop_event.is_set():
            if optimizer:
                current_perf = optimizer.get_next_config()
                if current_perf is None:
                    break
                current_perf = PerfConfig(
                    self._worker_count(current_perf.workers, 4),
                    self._worker_count(current_perf.sub_workers, 4),
                    current_perf.throughput,
                )
                optimizer.start_segment(current_perf)

            segment_albums = []
            files_in_segment = 0
            while pending_albums and files_in_segment < 10:
                album = pending_albums.pop(0)
                segment_albums.append(album)
                files_in_segment += len(album[1])

            with ThreadPoolExecutor(
                max_workers=current_perf.workers, thread_name_prefix="cover-album"
            ) as executor:
                futures = [
                    executor.submit(
                        self._process_folder_internal, folder, files, scan_result,
                        current_perf.sub_workers, optimizer, progress_callback, total_dirty
                    )
                    for folder, files in segment_albums
                ]
                for future in as_completed(futures):
                    if self.stop_event.is_set():
                        for pending in futures:
                            pending.cancel()
                        break
                    try:
                        self.cache.update_entries(future.result())
                    except Exception:
                        LOGGER.exception("Album processing worker failed")

            if optimizer and not self.stop_event.is_set():
                optimizer.end_segment()

        if optimizer and not self.stop_event.is_set():
            if optimizer.save_result(self.config.data):
                self.config.save()

    def _process_folder_internal(
        self, folder, files, scan_result, sub_workers, optimizer,
        progress_callback, total_dirty
    ):
        jpeg_cache = {}
        files_to_update = []
        cache_updates = []

        for file_path in files:
            if self.stop_event.is_set():
                break
            try:
                images = scan_result.dirty_images.get(file_path)
                if images is None:
                    images = processor.get_images_info(file_path)
                if not images:
                    cache_updates.append((str(file_path), os.path.getmtime(file_path), "no_cover"))
                    continue

                for image in images:
                    if image.mime != processor.JPEG_MIME:
                        if image.hash not in jpeg_cache:
                            jpeg_cache[image.hash] = processor.to_jpeg_bytes(
                                image.data,
                                resolve_ffmpeg_path(self.config.data.get("ffmpeg_path")),
                            )
                        image.data = jpeg_cache[image.hash]
                        image.mime = processor.JPEG_MIME
                files_to_update.append((file_path, images))
            except Exception as exc:
                LOGGER.warning("Artwork preparation failed for %s: %s", file_path, exc)
                status = str(exc)
                if not status.startswith("error:"):
                    status = f"error:unknown:{status}"
                try:
                    cache_updates.append((str(file_path), os.path.getmtime(file_path), status))
                except OSError:
                    pass
                self._update_progress_atomic(progress_callback, total_dirty, file_path.name, optimizer)

        def update_one(file_path, images):
            if self.stop_event.is_set():
                return None
            try:
                processor.update_audio_images(file_path, images)
                status = "ok"
            except Exception as exc:
                LOGGER.warning("Could not update artwork in %s: %s", file_path, exc)
                status = str(exc)
                if not status.startswith("error:"):
                    status = f"error:unknown:{status}"
            try:
                entry = (str(file_path), os.path.getmtime(file_path), status)
            except OSError:
                entry = (str(file_path), 0.0, "error:missing")
            self._update_progress_atomic(progress_callback, total_dirty, file_path.name, optimizer)
            return entry

        with ThreadPoolExecutor(
            max_workers=self._worker_count(sub_workers, 4),
            thread_name_prefix="cover-file"
        ) as executor:
            futures = [executor.submit(update_one, path, images) for path, images in files_to_update]
            for future in as_completed(futures):
                try:
                    entry = future.result()
                    if entry:
                        cache_updates.append(entry)
                except Exception:
                    LOGGER.exception("Unexpected file update worker failure")

        return cache_updates

    def _update_progress_atomic(self, callback, total, name, optimizer):
        with self._lock:
            self.processed_count += 1
            if optimizer:
                optimizer.record_file()
            if callback:
                try:
                    callback(self.processed_count, max(1, total), name)
                except Exception:
                    LOGGER.exception("Processing progress callback failed")

    def _get_env_id(self, path):
        windows_path = PureWindowsPath(str(path))
        is_unc = str(path).startswith("\\\\") or windows_path.drive.startswith("\\\\")
        return f"{platform.node()}_{os.cpu_count()}_{'UNC' if is_unc else 'Local'}"

    def stop(self):
        self.stop_event.set()
