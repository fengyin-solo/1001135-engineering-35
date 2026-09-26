"""港口集装箱作业调度平台 后端服务入口。

启动：uvicorn app.main:app --host 127.0.0.1 --port 8000
健康检查：GET /api/health
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import ROUTERS
from app.store import store


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    if store.seeded_modules:
        print(f"[启动] 已生成示例数据，覆盖模块：{'、'.join(store.seeded_modules)}", flush=True)
    else:
        print("[启动] 已加载本地数据文件，未重复生成示例数据", flush=True)
    print(f"[启动] 数据文件：{settings.db_path}", flush=True)
    yield


app = FastAPI(title="港口集装箱作业调度平台", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def persist_after_write(request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
    """写操作成功后把数据落盘：刷新页面、重启服务，看到的数字都一样。"""
    response = await call_next(request)
    if request.method not in ("GET", "HEAD", "OPTIONS") and response.status_code < 400:
        store.persist()
    return response


for module in ROUTERS:
    app.include_router(module.router)


@app.get("/api/health")
def health() -> dict[str, object]:
    """健康检查：确认服务已经监听、示例数据已经就绪。"""
    return {"ok": True, "app": settings.app_name, "modules": len(store.module_names())}


@app.get("/api/overview")
def overview() -> dict[str, object]:
    """运营概览：把各业务模块的待处理量汇总成看板卡片。"""
    return store.overview()
