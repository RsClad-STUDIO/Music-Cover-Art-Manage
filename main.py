"""Compatibility entry point for the CLI application."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from music_cover_art_manage.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
