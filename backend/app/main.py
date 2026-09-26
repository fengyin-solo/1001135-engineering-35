"""港口集装箱作业调度平台 后端服务入口。

启动：uvicorn app.main:app --host 127.0.0.1 --port 8000
健康检查：GET /api/health

frontend/dist 存在时（执行过 `npm run build`），后端会顺带托管构建产物，
未匹配的 GET 路径回退到 index.html，刷新页面不会 404；构建产物与本地
dev server 用同一份数据文件，看到的数字一致。
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException
from starlette.responses import Response
from starlette.types import Scope

from app.config import settings
from app.routers import ROUTERS
from app.store import store

app = FastAPI(title="港口集装箱作业调度平台", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    # 本地调试端口可能顺延（5174、5175……），本机来源一律放行
    allow_origin_regex=r"https?://(127\.0\.0\.1|localhost)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for module in ROUTERS:
    app.include_router(module.router)


@app.get("/api/health")
def health() -> dict[str, object]:
    """健康检查：确认服务已经监听、示例数据已经就绪。"""
    return {
        "ok": True,
        "app": settings.app_name,
        "modules": len(store.module_names()),
        "entries": store.total_entries(),
        "database": str(store.db_path),
    }


@app.get("/api/overview")
def overview() -> dict[str, object]:
    """运营概览：把各业务模块的待处理量汇总成看板卡片。"""
    return store.overview()


class SpaStaticFiles(StaticFiles):
    """静态资源之外的路径一律回退到 index.html，交给前端路由处理。

    /api 下的未知路径不回退：接口地址写错时应得到 404，而不是一个
    200 的 HTML 页面。
    """

    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except HTTPException as exc:
            if exc.status_code != 404 or path == "api" or path.startswith("api/"):
                raise
            return await super().get_response("index.html", scope)


DIST_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if DIST_DIR.is_dir():
    # 挂在 API 路由之后：/api/* 仍走接口，其余路径才进构建产物
    app.mount("/", SpaStaticFiles(directory=DIST_DIR, html=True), name="dist")
