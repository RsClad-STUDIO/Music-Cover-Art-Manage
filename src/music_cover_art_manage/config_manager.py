import json
import logging
import os
import shutil
import sys
import tempfile
from pathlib import Path

CONFIG_FILE = str(get_app_dir() / "config.json")
LOGGER = logging.getLogger(__name__)


def get_app_dir() -> Path:
    """Return the directory containing the executable or source entry point."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def get_bundled_ffmpeg() -> Path:
    return get_app_dir() / "ffmpeg" / "ffmpeg.exe"


def resolve_ffmpeg_path(configured_path=None) -> str:
    """Resolve FFmpeg in this order: explicit setting, bundled copy, PATH."""
    if configured_path:
        candidate = Path(os.path.expandvars(os.path.expanduser(str(configured_path).strip().strip('"'))))
        if candidate.is_file():
            return str(candidate.resolve())

    bundled = get_bundled_ffmpeg()
    if bundled.is_file():
        return str(bundled)

    discovered = shutil.which("ffmpeg")
    if discovered:
        return discovered

    # Preserve the legacy default as a visible, editable fallback in the GUI.
    return str(configured_path or r"C:\ffmpeg\bin\ffmpeg.exe")


class Config:
    def __init__(self):
        self.data = {
            "music_dir": "",
            "ffmpeg_path": str(get_bundled_ffmpeg()),
            "workers": "Auto",
            "sub_workers": "Auto",
            "optimized_results": {},
        }
        self.load()

    def load(self):
        if not os.path.exists(CONFIG_FILE):
            return

        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as file:
                loaded = json.load(file)
            if not isinstance(loaded, dict):
                raise ValueError("Configuration root must be a JSON object")
            self.data.update(loaded)
            self._normalize()
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            LOGGER.warning("Could not load %s: %s", CONFIG_FILE, exc)

    def _normalize(self):
        if not isinstance(self.data.get("music_dir"), str):
            self.data["music_dir"] = ""
        if not isinstance(self.data.get("ffmpeg_path"), str):
            self.data["ffmpeg_path"] = str(get_bundled_ffmpeg())

        for key in ("workers", "sub_workers"):
            value = self.data.get(key, "Auto")
            if value == "Auto":
                continue
            try:
                value = int(value)
            except (TypeError, ValueError):
                value = "Auto"
            if value != "Auto":
                value = max(1, min(32, value))
            self.data[key] = value

        if not isinstance(self.data.get("optimized_results"), dict):
            self.data["optimized_results"] = {}

    def save(self):
        directory = os.path.dirname(os.path.abspath(CONFIG_FILE))
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", newline="\n",
                dir=directory, prefix=".config-", suffix=".tmp",
                delete=False
            ) as file:
                temp_path = file.name
                json.dump(self.data, file, indent=4, ensure_ascii=False)
                file.write("\n")
                file.flush()
                os.fsync(file.fileno())
            os.replace(temp_path, CONFIG_FILE)
            return True
        except (OSError, TypeError, ValueError) as exc:
            LOGGER.exception("Could not save %s: %s", CONFIG_FILE, exc)
            if temp_path:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
            return False
