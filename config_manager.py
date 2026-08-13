import json
import os
import sys

CONFIG_FILE = "config.json"


def get_app_dir():
    """アプリケーション本体が存在するディレクトリを取得する。"""
    if getattr(sys, "frozen", False):
        # PyInstallerでEXE化された場合
        return os.path.dirname(sys.executable)

    # Pythonから直接実行している場合
    return os.path.dirname(os.path.abspath(__file__))


def get_bundled_ffmpeg():
    """アプリに同梱されたFFmpegのパスを取得する。"""
    return os.path.join(get_app_dir(), "ffmpeg", "ffmpeg.exe")


class Config:
    def __init__(self):
        self.data = {
            "music_dir": "",
            "ffmpeg_path": "",
            "workers": 8
        }

        self.load()
        self.ensure_ffmpeg_path()

    def load(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    self.data.update(json.load(f))
            except Exception:
                pass

    def save(self):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(
                self.data,
                f,
                indent=4,
                ensure_ascii=False
            )

    def ensure_ffmpeg_path(self):
        """FFmpegのパスを決定する。"""

        # 現在設定されているFFmpegが存在するなら、そのまま使用
        current_path = self.data.get("ffmpeg_path", "")

        if current_path and os.path.isfile(current_path):
            return

        # アプリ同梱FFmpegを探す
        bundled_path = get_bundled_ffmpeg()

        if os.path.isfile(bundled_path):
            self.data["ffmpeg_path"] = bundled_path
            return

        # 最後にPATHからffmpeg.exeを探す
        path_ffmpeg = "ffmpeg.exe"

        if os.system("where ffmpeg.exe >nul 2>&1") == 0:
            self.data["ffmpeg_path"] = path_ffmpeg
            return

        # 見つからない場合
        self.data["ffmpeg_path"] = ""