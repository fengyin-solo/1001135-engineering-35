"""运行配置：端口、跨域、数据文件位置。

默认值保证克隆下来就能跑；需要调整时用环境变量覆盖，不用改代码：
APP_ENV、APP_HOST、APP_PORT、APP_DB_PATH、APP_ALLOWED_ORIGINS（逗号分隔）。
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent


def _env(name: str, default: str) -> str:
    value = os.environ.get(name, "").strip()
    return value or default


@dataclass(frozen=True)
class Settings:
    app_name: str = "港口集装箱作业调度平台"
    env: str = field(default_factory=lambda: _env("APP_ENV", "local"))
    host: str = field(default_factory=lambda: _env("APP_HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: int(_env("APP_PORT", "8000")))
    # 本地数据文件：默认放在 backend/data/ 下，与前端构建产物 frontend/dist 互不干扰
    db_path: Path = field(
        default_factory=lambda: Path(_env("APP_DB_PATH", str(BACKEND_DIR / "data" / "app.db")))
    )
    allowed_origins: list[str] = field(
        default_factory=lambda: [
            origin.strip()
            for origin in _env(
                "APP_ALLOWED_ORIGINS",
                "http://127.0.0.1:5173,http://localhost:5173",
            ).split(",")
            if origin.strip()
        ]
    )
    page_size_default: int = 20
    page_size_max: int = 200


settings = Settings()
