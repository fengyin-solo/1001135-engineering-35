"""运行配置：端口、跨域、数据文件位置。

所有项都能用环境变量覆盖，默认值写在仓库里（见 .env.example），
不再靠口头约定：新同事不配置任何东西也能直接起服务。
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# backend/ 目录：数据文件默认放在这里，和代码、构建产物分开
BACKEND_DIR = Path(__file__).resolve().parent.parent


def _default_db_path() -> str:
    return str(BACKEND_DIR / "data" / "app.sqlite3")


@dataclass(frozen=True)
class Settings:
    app_name: str = "港口集装箱作业调度平台"
    env: str = os.getenv("APP_ENV", "local")
    port: int = int(os.getenv("APP_PORT", "8000"))
    # 本地数据文件：SQLite，落盘后重启不丢、不重复灌示例数据
    db_path: str = os.getenv("APP_DB_PATH", _default_db_path())
    allowed_origins: list[str] = field(
        default_factory=lambda: [
            "http://127.0.0.1:5173",
            "http://localhost:5173",
        ]
    )
    page_size_default: int = 20
    page_size_max: int = 200


settings = Settings()
