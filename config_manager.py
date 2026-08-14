import json
import os

CONFIG_FILE = "config.json"

class Config:
    def __init__(self):
        self.data = {
            "music_dir": "",
            "ffmpeg_path": r"C:\ffmpeg\bin\ffmpeg.exe",
            "workers": "Auto",
            "sub_workers": "Auto",
            "optimized_results": {}
        }
        self.load()

    def load(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    self.data.update(json.load(f))
            except:
                pass

    def save(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
        except:
            pass