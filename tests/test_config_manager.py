import json

import config_manager


def test_config_save_is_atomic_and_round_trips(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    monkeypatch.setattr(config_manager, "CONFIG_FILE", str(config_path))

    subject = config_manager.Config()
    subject.data["music_dir"] = r"Y:\Music"
    assert subject.save() is True

    loaded = config_manager.Config()
    assert loaded.data["music_dir"] == r"Y:\Music"
    assert json.loads(config_path.read_text(encoding="utf-8"))["music_dir"] == r"Y:\Music"


def test_invalid_config_does_not_crash(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    config_path.write_text("{invalid", encoding="utf-8")
    monkeypatch.setattr(config_manager, "CONFIG_FILE", str(config_path))

    subject = config_manager.Config()
    assert subject.data["music_dir"] == ""


def test_config_normalizes_invalid_values(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({
            "music_dir": None,
            "ffmpeg_path": 42,
            "workers": "invalid",
            "sub_workers": 100,
            "optimized_results": [],
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(config_manager, "CONFIG_FILE", str(config_path))

    subject = config_manager.Config()
    assert subject.data["music_dir"] == ""
    assert subject.data["ffmpeg_path"].endswith("ffmpeg.exe")
    assert subject.data["workers"] == "Auto"
    assert subject.data["sub_workers"] == 32
    assert subject.data["optimized_results"] == {}


def test_bundled_ffmpeg_is_used_when_saved_path_is_missing(tmp_path, monkeypatch):
    bundled = tmp_path / "ffmpeg" / "ffmpeg.exe"
    bundled.parent.mkdir()
    bundled.write_bytes(b"")
    monkeypatch.setattr(config_manager, "get_bundled_ffmpeg", lambda: bundled)
    monkeypatch.setattr(config_manager.shutil, "which", lambda _name: None)

    resolved = config_manager.resolve_ffmpeg_path(str(tmp_path / "missing.exe"))

    assert resolved == str(bundled)


def test_explicit_ffmpeg_path_takes_precedence(tmp_path, monkeypatch):
    custom = tmp_path / "custom-ffmpeg.exe"
    custom.write_bytes(b"")
    bundled = tmp_path / "ffmpeg" / "ffmpeg.exe"
    bundled.parent.mkdir()
    bundled.write_bytes(b"")
    monkeypatch.setattr(config_manager, "get_bundled_ffmpeg", lambda: bundled)

    assert config_manager.resolve_ffmpeg_path(str(custom)) == str(custom.resolve())
