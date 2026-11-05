from types import SimpleNamespace

import processor
from core_engine import CoreEngine


class MemoryCache:
    def __init__(self, entries):
        self.entries = entries

    def load_all_to_dict(self):
        return dict(self.entries)


class FakeConfig:
    data = {"workers": 1}


def test_cached_dirty_file_is_reloaded_for_conversion(tmp_path, monkeypatch):
    audio_file = tmp_path / "track.mp3"
    audio_file.write_bytes(b"placeholder")
    mtime = audio_file.stat().st_mtime
    calls = []

    def fake_get_images(path):
        calls.append(path)
        return [SimpleNamespace(mime="image/png", hash="cover", data=b"png")]

    monkeypatch.setattr(processor, "get_images_info", fake_get_images)
    cache = MemoryCache({str(audio_file): (mtime, "dirty")})
    engine = CoreEngine(FakeConfig(), cache)

    result = engine.scan(str(tmp_path))

    assert len(calls) == 1
    assert result.stats["dirty"] == 1
    assert audio_file in result.dirty_images
    assert result.groups[audio_file.parent] == [audio_file]


def test_cached_error_is_retried_on_next_scan(tmp_path, monkeypatch):
    audio_file = tmp_path / "track.mp3"
    audio_file.write_bytes(b"placeholder")
    mtime = audio_file.stat().st_mtime
    calls = []

    def fail_read(_path):
        calls.append(True)
        raise RuntimeError("error:permission")

    monkeypatch.setattr(processor, "get_images_info", fail_read)
    cache = MemoryCache({str(audio_file): (mtime, "error:permission")})
    engine = CoreEngine(FakeConfig(), cache)

    result = engine.scan(str(tmp_path))

    assert calls == [True]
    assert result.stats["error"] == 1
    assert result.scanned_data == [(str(audio_file), mtime, "error:permission")]


def test_scan_respects_cancellation_requested_before_start(tmp_path):
    engine = CoreEngine(FakeConfig(), MemoryCache({}))
    engine.stop()

    result = engine.scan(str(tmp_path))

    assert result.stats["total"] == 0
    assert result.cancelled is True


def test_process_respects_cancellation_requested_before_start(tmp_path):
    from core_engine import ScanResult

    engine = CoreEngine(FakeConfig(), MemoryCache({}))
    engine.stop()
    scan_result = ScanResult()
    scan_result.stats["dirty"] = 1
    audio_file = tmp_path / "track.mp3"
    scan_result.groups[audio_file.parent].append(audio_file)

    summary = engine.process(scan_result)

    assert summary == {"success": 0, "error": 0, "skipped": 0, "cancelled": True}
