from concurrent.futures import ThreadPoolExecutor

import cache_manager


def test_cache_serializes_concurrent_writes(tmp_path, monkeypatch):
    monkeypatch.setattr(cache_manager, "CACHE_FILE", str(tmp_path / "cache.db"))
    cache = cache_manager.Cache()
    entries = [
        (str(tmp_path / f"track-{index}.mp3"), float(index), "ok")
        for index in range(100)
    ]

    try:
        with ThreadPoolExecutor(max_workers=8) as executor:
            list(executor.map(lambda entry: cache.set_entry(*entry), entries))

        loaded = cache.load_all_to_dict()
        assert len(loaded) == 100
        assert all(loaded[path] == (mtime, status) for path, mtime, status in entries)
    finally:
        cache.close()
