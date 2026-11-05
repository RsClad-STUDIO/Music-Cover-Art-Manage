import hashlib
import logging
import os
import subprocess
import unicodedata
from pathlib import Path

from mutagen import MutagenError
from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3, APIC, ID3NoHeaderError
from mutagen.mp4 import MP4, MP4Cover

LOGGER = logging.getLogger(__name__)
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
    for char in str(s):
        char_width = 2 if unicodedata.east_asian_width(char) in ("W", "F") else 1
        if current + char_width > width:
            break
        result.append(char)
        current += char_width
    return "".join(result) + " " * max(0, width - current)


def to_jpeg_bytes(image_bytes: bytes, ffmpeg_path: str) -> bytes:
    executable = str(ffmpeg_path or "").strip().strip('"')
    if not executable or not Path(executable).is_file():
        raise RuntimeError(f"error:ffmpeg:not_found:{executable or '(empty path)'}")

    command = [
        executable, "-hide_banner", "-loglevel", "error", "-nostdin",
        "-y", "-i", "pipe:0", "-frames:v", "1", "-f", "mjpeg",
        "-vcodec", "mjpeg", "-q:v", "3", "pipe:1",
    ]
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    try:
        completed = subprocess.run(
            command, input=image_bytes, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, timeout=30, check=True,
            creationflags=creationflags,
        )
        if not completed.stdout:
            raise RuntimeError("FFmpeg returned an empty JPEG image")
        return completed.stdout
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.decode("utf-8", errors="replace").strip()
        LOGGER.warning("FFmpeg conversion failed: %s", detail[-2000:])
        raise RuntimeError(f"error:ffmpeg:{detail[-1000:]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("error:ffmpeg:timeout") from exc
    except OSError as exc:
        raise RuntimeError(f"error:ffmpeg:launch:{exc}") from exc


def get_images_info(path: Path):
    path = Path(path)
    ext = path.suffix.lower()
    images = []
    try:
        if ext == ".mp3":
            try:
                tags = ID3(str(path))
            except ID3NoHeaderError:
                return []
            for key in tags.keys():
                if key.startswith("APIC"):
                    picture = tags[key]
                    images.append(ImageInfo(
                        picture.data, picture.mime, picture.type,
                        picture.desc, compute_hash(picture.data)
                    ))
        elif ext == ".flac":
            audio = FLAC(str(path))
            for picture in audio.pictures:
                images.append(ImageInfo(
                    picture.data, picture.mime, picture.type,
                    picture.desc, compute_hash(picture.data)
                ))
        elif ext in (".m4a", ".mp4"):
            audio = MP4(str(path))
            if audio.tags and "covr" in audio.tags:
                for cover in audio.tags["covr"]:
                    mime = JPEG_MIME if cover.imageformat == MP4Cover.FORMAT_JPEG else "image/png"
                    data = bytes(cover)
                    images.append(ImageInfo(data, mime, 3, "", compute_hash(data)))
    except PermissionError as exc:
        raise RuntimeError("error:permission") from exc
    except (OSError, MutagenError, ValueError) as exc:
        raise RuntimeError(f"error:corrupt:{exc}") from exc
    except Exception as exc:
        LOGGER.exception("Unexpected artwork read error for %s", path)
        raise RuntimeError(f"error:unknown:{exc}") from exc
    return images


def update_audio_images(path: Path, updated_images: list):
    """Replace embedded artwork while retaining supported artwork metadata."""
    path = Path(path)
    ext = path.suffix.lower()
    try:
        if ext == ".mp3":
            try:
                tags = ID3(str(path))
            except ID3NoHeaderError:
                tags = ID3()
            for key in [key for key in tags.keys() if key.startswith("APIC")]:
                del tags[key]
            for image in updated_images:
                tags.add(APIC(
                    encoding=3, mime=JPEG_MIME, type=image.type,
                    desc=image.desc, data=image.data
                ))
            version = tags.version[1] if tags.version and tags.version[0] == 2 else 4
            tags.save(str(path), v2_version=version)
        elif ext == ".flac":
            audio = FLAC(str(path))
            audio.clear_pictures()
            for image in updated_images:
                picture = Picture()
                picture.type = image.type
                picture.mime = JPEG_MIME
                picture.desc = image.desc
                picture.data = image.data
                audio.add_picture(picture)
            audio.save()
        elif ext in (".m4a", ".mp4"):
            audio = MP4(str(path))
            if audio.tags is None:
                audio.add_tags()
            audio.tags["covr"] = [
                MP4Cover(image.data, imageformat=MP4Cover.FORMAT_JPEG)
                for image in updated_images
            ]
            audio.save()
        else:
            raise RuntimeError(f"error:unsupported_format:{ext}")
    except MutagenError as exc:
        raise RuntimeError(f"error:mutagen:{exc}") from exc
    except PermissionError as exc:
        raise RuntimeError("error:permission") from exc
    except OSError as exc:
        raise RuntimeError(f"error:io:{exc}") from exc
    except RuntimeError:
        raise
    except Exception as exc:
        LOGGER.exception("Unexpected artwork write error for %s", path)
        raise RuntimeError(f"error:unknown:{exc}") from exc
