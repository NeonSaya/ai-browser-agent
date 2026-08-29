"""桌面入口：后台起 uvicorn，pywebview 开原生窗口加载页面。

打包：uv run python scripts/build_exe.py 产出 all-in-one EXE（onedir）。
开发：uv run python -m api.desktop（需先构建前端：cd frontend && npm run build）。
"""

from __future__ import annotations

import os
import sys
import threading
from pathlib import Path


def _setup_frozen_env() -> None:
    """打包模式：把 Playwright 浏览器路径指向包内目录（all-in-one）。"""
    if not getattr(sys, "frozen", False):
        return
    bundled = Path(sys.executable).resolve().parent / "browsers"
    if bundled.is_dir():
        os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(bundled))


def _find_free_port() -> int:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main() -> None:
    _setup_frozen_env()

    # 窗口模式（无控制台）下 stdout/stderr 为 None，重定向到 devnull，
    # 避免 uvicorn/loguru 等组件写入时崩溃。此处进程级长生命周期，不能用 with
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")  # noqa: SIM115
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")  # noqa: SIM115

    port = _find_free_port()
    url = f"http://127.0.0.1:{port}"

    import uvicorn

    server = uvicorn.Server(
        uvicorn.Config(
            "api.app:app",
            host="127.0.0.1",
            port=port,
            log_level="warning",
            # 窗口模式（无控制台）下没有 stdout/stderr，禁用 uvicorn 日志配置
            log_config=None,
        )
    )
    threading.Thread(target=server.run, daemon=True).start()

    import webview

    webview.create_window(
        "WebAgent",
        url,
        width=1280,
        height=860,
        min_size=(960, 640),
    )
    webview.start()


if __name__ == "__main__":
    main()
