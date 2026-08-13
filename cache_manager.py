import sqlite3
import os
from typing import Optional, Tuple, List, Dict

CACHE_FILE = "cache.db"

class Cache:
    def __init__(self):
        self.conn = sqlite3.connect(CACHE_FILE, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.conn.execute("PRAGMA synchronous = NORMAL")
        self._create_table()

    def _create_table(self):
        with self.conn:
            self.conn.execute('CREATE TABLE IF NOT EXISTS files (path TEXT PRIMARY KEY, mtime REAL, status TEXT)')

    def get_entry(self, path: str) -> Optional[Tuple[float, str]]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT mtime, status FROM files WHERE path = ?", (path,))
        return cursor.fetchone()

    def set_entry(self, path: str, mtime: float, status: str):
        with self.conn:
            self.conn.execute("INSERT OR REPLACE INTO files VALUES (?, ?, ?)", (path, mtime, status))

    def update_entries(self, entries: List[Tuple[str, float, str]]):
        if not entries: return
        with self.conn:
            self.conn.executemany("INSERT OR REPLACE INTO files VALUES (?, ?, ?)", entries)

    def load_all_to_dict(self) -> Dict[str, Tuple[float, str]]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT path, mtime, status FROM files")
        return {row[0]: (row[1], row[2]) for row in cursor.fetchall()}

    def close(self):
        self.conn.close()
