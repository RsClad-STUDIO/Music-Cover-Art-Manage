import sys
import os
import signal
from pathlib import Path
from config_manager import Config
from cache_manager import Cache
from core_engine import CoreEngine
import processor

def main():
    config = Config()
    cache = Cache()
    engine = CoreEngine(config, cache)
    signal.signal(signal.SIGINT, lambda s, f: engine.stop_event.set())

    if not config.data["music_dir"]:
        config.data["music_dir"] = input("Music Directory Path: ").strip('"')
        config.save()

    print(f"\n[1/2] Scanning: {config.data['music_dir']}")
    def p_scan(c, t, name):
        sys.stdout.write(f"\rScanning: [{c}/{t}] {processor.fit_to_width(name, 30)}")
        sys.stdout.flush()

    res = engine.scan(config.data["music_dir"], p_scan)
    cache.update_entries(res.scanned_data)
    
    s = res.stats
    print(f"\n\nScan Result:\n - Total: {s['total']}\n - To Process: {s['dirty']}\n - Already JPEG: {s['already_jpeg']}\n - No Cover: {s['no_cover']}")
    
    if s['dirty'] == 0:
        input("\nNo files to process. Press Enter to exit...")
        return

    if input("\nStart conversion? (y/n): ").lower() != 'y':
        input("\nCancelled. Press Enter to exit...")
        return

    print("\n[2/2] Processing...")
    def p_proc(c, t, name):
        sys.stdout.write(f"\rProgress: [{c}/{t}] {processor.fit_to_width(name, 30)}")
        sys.stdout.flush()

    engine.process(res, p_proc)
    print("\n\nFinished.")
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()