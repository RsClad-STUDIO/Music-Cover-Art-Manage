import logging
import signal
import sys

from cache_manager import Cache
from config_manager import Config, resolve_ffmpeg_path
from core_engine import CoreEngine
import processor

LOGGER = logging.getLogger(__name__)


def main():
    config = Config()
    cache = Cache()
    engine = CoreEngine(config, cache)
    signal.signal(signal.SIGINT, lambda _signum, _frame: engine.stop())

    try:
        if not config.data.get("music_dir"):
            path = input("Music Directory Path: ").strip().strip('"')
            config.data["music_dir"] = path
            config.save()

        config.data["music_dir"] = str(config.data.get("music_dir", "")).strip().strip('"')
        if not config.data["music_dir"]:
            print("No music directory was specified.")
            return 2

        ffmpeg_path = resolve_ffmpeg_path(config.data.get("ffmpeg_path"))
        print(f"\n[1/2] Scanning: {config.data['music_dir']}")

        def scan_progress(current, total, name):
            sys.stdout.write(
                f"\rScanning: [{current}/{total}] {processor.fit_to_width(name, 30)}"
            )
            sys.stdout.flush()

        result = engine.scan(config.data["music_dir"], scan_progress)
        cache.update_entries(result.scanned_data)

        stats = result.stats
        print(
            "\n\nScan Result:\n"
            f" - Total: {stats['total']}\n"
            f" - To Process: {stats['dirty']}\n"
            f" - Already JPEG: {stats['already_jpeg']}\n"
            f" - No Cover: {stats['no_cover']}\n"
            f" - Errors: {stats['error']}"
        )

        if engine.stop_event.is_set():
            print("\nScan cancelled.")
            return 130
        if stats["dirty"] == 0:
            print("\nNo files need processing.")
            return 0

        if input("\nStart conversion? (y/n): ").strip().lower() != "y":
            return 0

        config.data["ffmpeg_path"] = ffmpeg_path
        print("\n[2/2] Processing...")

        def process_progress(current, total, name):
            sys.stdout.write(
                f"\rProgress: [{current}/{total}] {processor.fit_to_width(name, 30)}"
            )
            sys.stdout.flush()

        engine.process(result, process_progress)
        if engine.stop_event.is_set():
            print("\n\nProcessing cancelled.")
            return 130
        print("\n\nFinished.")
        return 0
    except KeyboardInterrupt:
        engine.stop()
        print("\nCancelled.")
        return 130
    except Exception:
        LOGGER.exception("CLI operation failed")
        print("\nAn unexpected error occurred. See the log for details.")
        return 1
    finally:
        cache.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.StreamHandler()],
    )
    raise SystemExit(main())
