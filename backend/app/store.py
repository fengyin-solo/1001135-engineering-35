"""本地数据仓库：示例数据与业务记录都落在 SQLite 文件里，重启不丢、不重复。

- 数据文件默认在 ``backend/data/app.db``（可用 APP_DB_PATH 覆盖），与前端构建产物
  ``frontend/dist`` 分属两棵目录树，互不影响。
- 首次启动时把 ``app.seed.SEED_ROWS`` 灌入数据库；某个模块表里已有数据就跳过，
  所以重复起服务不会重复塞入示例数据。想重置数据，停服务后删掉数据文件即可。
- 对上层暴露的接口与原来的内存版一致（rows/find/overview），另加 add/save
  两个写方法：读走内存缓存，写会同步落盘。
"""
from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

from app.config import settings
from app.seed import SEED_ROWS

_SCHEMA = """
CREATE TABLE IF NOT EXISTS entries (
    module   TEXT NOT NULL,
    entry_id INTEGER NOT NULL,
    payload  TEXT NOT NULL,
    PRIMARY KEY (module, entry_id)
)
"""


class Store:
    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = Path(db_path or settings.db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock, self._conn:
            self._conn.execute(_SCHEMA)
        self._tables: dict[str, list[dict[str, Any]]] = {}
        self.seeded_modules: list[str] = []
        self._seed_missing_modules()
        self._load_all()

    # ---------- 初始化 ----------

    def _seed_missing_modules(self) -> None:
        """只给空模块表灌示例数据：已有数据的模块原样保留，保证重复启动不重复塞数。"""
        with self._lock, self._conn:
            for module, rows in SEED_ROWS.items():
                (count,) = self._conn.execute(
                    "SELECT COUNT(*) FROM entries WHERE module = ?", (module,)
                ).fetchone()
                if count:
                    continue
                self._conn.executemany(
                    "INSERT INTO entries (module, entry_id, payload) VALUES (?, ?, ?)",
                    [
                        (module, int(row["id"]), json.dumps(row, ensure_ascii=False))
                        for row in rows
                    ],
                )
                self.seeded_modules.append(module)

    def _load_all(self) -> None:
        with self._lock:
            cursor = self._conn.execute(
                "SELECT module, payload FROM entries ORDER BY module, entry_id"
            )
            for row in cursor:
                self._tables.setdefault(row["module"], []).append(
                    json.loads(row["payload"])
                )

    # ---------- 读 ----------

    @property
    def db_path(self) -> Path:
        return self._db_path

    def module_names(self) -> list[str]:
        return sorted(self._tables)

    def rows(self, module: str) -> list[dict[str, Any]]:
        return self._tables.setdefault(module, [])

    def find(self, module: str, entry_id: int) -> dict[str, Any] | None:
        for row in self.rows(module):
            if int(row.get("id", 0)) == entry_id:
                return row
        return None

    def total_entries(self) -> int:
        return sum(len(rows) for rows in self._tables.values())

    def overview(self) -> dict[str, object]:
        modules: list[dict[str, object]] = []
        for name in self.module_names():
            rows = self.rows(name)
            modules.append({
                "name": name,
                "created": len(rows),
                "pending": sum(1 for row in rows if row.get("pending")),
                "abnormal": sum(1 for row in rows if row.get("abnormal")),
            })
        cards = [
            {"label": "业务模块", "value": len(modules)},
            {"label": "今日新增", "value": sum(int(item["created"]) for item in modules)},
            {"label": "待处理", "value": sum(int(item["pending"]) for item in modules)},
            {"label": "异常量", "value": sum(int(item["abnormal"]) for item in modules)},
        ]
        return {"cards": cards, "modules": modules}

    # ---------- 写（内存缓存与 SQLite 同步更新） ----------

    def add(self, module: str, entry: dict[str, Any]) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO entries (module, entry_id, payload) VALUES (?, ?, ?)",
                (module, int(entry["id"]), json.dumps(entry, ensure_ascii=False)),
            )
            self.rows(module).append(entry)

    def save(self, module: str, entry: dict[str, Any]) -> None:
        """把调用方就地修改过的 entry 落盘；内存缓存里已是同一对象，无需再改。"""
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE entries SET payload = ? WHERE module = ? AND entry_id = ?",
                (json.dumps(entry, ensure_ascii=False), module, int(entry["id"])),
            )


store = Store()
