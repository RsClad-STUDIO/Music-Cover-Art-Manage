import logging
import sqlite3
import threading
from typing import Dict, List, Optional, Tuple

CACHE_FILE = "cache.db"
LOGGER = logging.getLogger(__name__)


class Cache:
    def __init__(self):
        self._lock = threading.RLock()
        self.conn = sqlite3.connect(
            CACHE_FILE, timeout=30, check_same_thread=False
        )
        self.conn.execute("PRAGMA busy_timeout = 30000")
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.conn.execute("PRAGMA synchronous = NORMAL")
        self._create_table()

    def _create_table(self):
        with self._lock, self.conn:
            self.conn.execute(
                "CREATE TABLE IF NOT EXISTS files "
                "(path TEXT PRIMARY KEY, mtime REAL, status TEXT)"
            )

    def get_entry(self, path: str) -> Optional[Tuple[float, str]]:
        with self._lock:
            cursor = self.conn.execute(
                "SELECT mtime, status FROM files WHERE path = ?", (path,)
            )
            return cursor.fetchone()

    def set_entry(self, path: str, mtime: float, status: str):
        self.update_entries([(path, mtime, status)])

    def update_entries(self, entries: List[Tuple[str, float, str]]):
        if not entries:
            return
        with self._lock, self.conn:
            self.conn.executemany(
                "INSERT OR REPLACE INTO files (path, mtime, status) VALUES (?, ?, ?)",
                entries,
            )

    def load_all_to_dict(self) -> Dict[str, Tuple[float, str]]:
        with self._lock:
            cursor = self.conn.execute("SELECT path, mtime, status FROM files")
            return {row[0]: (row[1], row[2]) for row in cursor.fetchall()}

    def close(self):
        with self._lock:
            if self.conn is not None:
                self.conn.close()
                self.conn = None
