import subprocess
import hashlib
import unicodedata
from pathlib import Path
from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3, APIC, ID3NoHeaderError
from mutagen.mp4 import MP4, MP4Cover
from mutagen import MutagenError

SUPPORTED_EXTENSIONS = {".mp3", ".flac", ".m4a", ".mp4"}
JPEG_MIME = "image/jpeg"

class ImageInfo:
    def __init__(self, data, mime, img_type, desc, data_hash):
        self.data = data
        self.mime = mime
        self.type = img_type
        self.desc = desc
        self.hash = data_hash

def compute_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def fit_to_width(s: str, width: int) -> str:
    result = []
    current = 0
    for c in s:
        cw = 2 if unicodedata.east_asian_width(c) in ("W", "F") else 1
        if current + cw > width: break
        result.append(c)
        current += cw
    return "".join(result) + " " * (width - current)

def to_jpeg_bytes(image_bytes: bytes, ffmpeg_path: str) -> bytes:
    try:
        cmd = [ffmpeg_path, "-y", "-i", "pipe:0", "-vframes", "1", "-f", "mjpeg", "-q:v", "3", "pipe:1"]
        process = subprocess.run(cmd, input=image_bytes, capture_output=True, timeout=20, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
        return process.stdout
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"error:ffmpeg:{e.stderr.decode(errors='replace')}")
    except Exception:
        raise RuntimeError("error:ffmpeg")

def get_images_info(path: Path):
    ext = path.suffix.lower()
    images = []
    try:
        if ext == ".mp3":
            try: tags = ID3(str(path))
            except ID3NoHeaderError: return []
            for k in [k for k in tags.keys() if k.startswith("APIC")]:
                ap = tags[k]
                images.append(ImageInfo(ap.data, ap.mime, ap.type, ap.desc, compute_hash(ap.data)))
        elif ext == ".flac":
            audio = FLAC(str(path))
            for pic in audio.pictures:
                images.append(ImageInfo(pic.data, pic.mime, pic.type, pic.desc, compute_hash(pic.data)))
        elif ext in (".m4a", ".mp4"):
            audio = MP4(str(path))
            if audio.tags and "covr" in audio.tags:
                for c in audio.tags["covr"]:
                    mime = JPEG_MIME if c.imageformat == MP4Cover.FORMAT_JPEG else "image/png"
                    d = bytes(c)
                    images.append(ImageInfo(d, mime, 3, "", compute_hash(d)))
    except PermissionError: raise RuntimeError("error:permission")
    except Exception as e: raise RuntimeError(f"error:corrupt:{str(e)}")
    return images

def update_audio_images(path: Path, updated_images: list):
    ext = path.suffix.lower()
    try:
        if ext == ".mp3":
            tags = ID3(str(path))
            for k in [k for k in tags.keys() if k.startswith("APIC")]: del tags[k]
            for img in updated_images:
                tags.add(APIC(encoding=3, mime=JPEG_MIME, type=img.type, desc=img.desc, data=img.data))
            tags.save()
        elif ext == ".flac":
            audio = FLAC(str(path))
            audio.clear_pictures()
            for img in updated_images:
                p = Picture(); p.type = img.type; p.mime = JPEG_MIME; p.desc = img.desc; p.data = img.data
                audio.add_picture(p)
            audio.save(padding=lambda x: x)
        elif ext in (".m4a", ".mp4"):
            audio = MP4(str(path))
            audio.tags["covr"] = [MP4Cover(img.data, imageformat=MP4Cover.FORMAT_JPEG) for img in updated_images]
            audio.save()
    except MutagenError: raise RuntimeError("error:mutagen")
    except PermissionError: raise RuntimeError("error:permission")
    except Exception as e: raise RuntimeError(f"error:unknown:{str(e)}")
