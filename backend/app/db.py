"""SQLite 落盘：把内存里的业务表整体快照写进本地文件，重启后原样读回。

只用标准库，表结构刻意简单（一张表存所有模块的 JSON 行）：
本地开发的数据量很小，可靠性比查询灵活性重要。
"""
from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

_SCHEMA = """
CREATE TABLE IF NOT EXISTS module_rows (
    module  TEXT NOT NULL,
    row_id  INTEGER NOT NULL,
    payload TEXT NOT NULL,
    PRIMARY KEY (module, row_id)
)
"""


class Database:
    """本地 SQLite 文件的整体读写；多次写之间用锁串行化。"""

    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self._lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def load(self) -> dict[str, list[dict[str, Any]]]:
        """读出全部模块的行；文件不存在或为空时返回空 dict。"""
        tables: dict[str, list[dict[str, Any]]] = {}
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT module, payload FROM module_rows ORDER BY module, row_id"
            ).fetchall()
        for module, payload in rows:
            tables.setdefault(module, []).append(json.loads(payload))
        return tables

    def save(self, tables: dict[str, list[dict[str, Any]]]) -> None:
        """把当前内存表整体落盘：先清再写，一个事务里完成。"""
        flat = [
            (module, int(row.get("id", index + 1)), json.dumps(row, ensure_ascii=False))
            for module, rows in tables.items()
            for index, row in enumerate(rows)
        ]
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM module_rows")
            conn.executemany(
                "INSERT INTO module_rows (module, row_id, payload) VALUES (?, ?, ?)",
                flat,
            )
