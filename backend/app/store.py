"""数据仓库：示例数据只生成一次，之后每次启动从本地 SQLite 文件读回。

启动逻辑（幂等，重复起服务不会重复灌数据）：
1. 先读本地数据文件；只保留当前仍存在的业务模块，避免旧版本残留。
2. 某个模块在文件里没有任何行时，才用 SEED_ROWS 给它补示例数据。
3. 运行期的增改通过 persist() 落盘，刷新页面、重启服务数字都不变。
"""
from __future__ import annotations

from typing import Any

from app.config import settings
from app.db import Database
from app.seed import SEED_ROWS


class Store:
    def __init__(self, db: Database | None = None) -> None:
        self._db = db
        loaded = db.load() if db else {}
        self._tables: dict[str, list[dict[str, Any]]] = {
            name: rows for name, rows in loaded.items() if name in SEED_ROWS
        }
        self._seeded: list[str] = []
        for name, seed_rows in SEED_ROWS.items():
            if not self._tables.get(name):
                self._tables[name] = [dict(row) for row in seed_rows]
                self._seeded.append(name)
        if self._seeded or len(self._tables) != len(loaded):
            self.persist()

    @property
    def seeded_modules(self) -> list[str]:
        """本次启动新灌了示例数据的模块；为空表示直接沿用了本地数据。"""
        return list(self._seeded)

    def persist(self) -> None:
        """把当前数据整体落盘；每次写操作后由应用层调用。"""
        if self._db is not None:
            self._db.save(self._tables)

    def module_names(self) -> list[str]:
        return sorted(self._tables)

    def rows(self, module: str) -> list[dict[str, Any]]:
        return self._tables.setdefault(module, [])

    def find(self, module: str, entry_id: int) -> dict[str, Any] | None:
        for row in self.rows(module):
            if int(row.get("id", 0)) == entry_id:
                return row
        return None

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


store = Store(db=Database(settings.db_path))
