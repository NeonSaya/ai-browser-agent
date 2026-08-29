"""FastAPI 应用工厂：REST + WebSocket + 前端静态资源托管。

开发模式下前端走 Vite dev server（代理 /api）；生产模式下直接托管 frontend/dist。
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from api.context import get_bus, get_log_buffer
from api.routes import config, health, logs, tasks, ws


def _mount_frontend(app: FastAPI) -> None:
    """生产模式：托管 frontend/dist；目录不存在时跳过（开发模式）。

    源码模式从项目根目录找；打包模式从 PyInstaller 解包目录（_internal）找。
    """
    import sys

    if getattr(sys, "frozen", False):
        dist = Path(sys._MEIPASS) / "frontend" / "dist"  # type: ignore[attr-defined]
    else:
        dist = Path(__file__).resolve().parents[1] / "frontend" / "dist"
    if dist.is_dir() and (dist / "index.html").is_file():
        app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        import asyncio

        from loguru import logger

        from webagent.core.logger import init_logger
        from webagent.core.storage import init_db

        init_logger()
        init_db()
        get_bus().bind_loop(asyncio.get_running_loop())
        # 日志 sink：环形缓冲 + WS 推送；DEBUG 全量记录，展示层自行过滤
        _sink_id = logger.add(
            get_log_buffer(),
            level="DEBUG",
            enqueue=False,  # sink 内部只是 append + call_soon_threadsafe，无需再异步
        )
        logger.info("API 服务就绪")
        yield
        logger.remove(_sink_id)

    app = FastAPI(title="WebAgent API", version="0.1.0", lifespan=lifespan)
    app.include_router(health.router)
    app.include_router(tasks.router)
    app.include_router(config.router)
    app.include_router(logs.router)
    app.include_router(ws.router)

    _mount_frontend(app)
    return app


app = create_app()
