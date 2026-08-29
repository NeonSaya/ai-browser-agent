"""跨线程事件总线：Agent 工作线程 -> asyncio 事件循环 -> WebSocket 客户端。"""

from __future__ import annotations

import asyncio
from typing import Any


class EventBus:
    """线程安全的事件广播器。

    Agent 在后台线程中调用 publish()；事件被投递到 asyncio 事件循环，
    再分发给所有订阅者（每个 WS 连接一个 asyncio.Queue）。
    """

    def __init__(self, queue_size: int = 500) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._subscribers: set[asyncio.Queue[dict[str, Any]]] = set()
        self._queue_size = queue_size

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """在 FastAPI lifespan 启动时绑定事件循环（仅一次）。"""
        self._loop = loop

    def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=self._queue_size)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        self._subscribers.discard(queue)

    def publish(self, event: dict[str, Any]) -> None:
        """从任意线程发布事件；无订阅者或循环未就绪时静默丢弃。"""
        loop = self._loop
        if loop is None or loop.is_closed():
            return

        def _dispatch() -> None:
            for queue in list(self._subscribers):
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    # 慢客户端丢帧，避免阻塞其他订阅者
                    pass

        try:
            loop.call_soon_threadsafe(_dispatch)
        except RuntimeError:
            # 事件循环已关闭（进程退出中）
            pass
