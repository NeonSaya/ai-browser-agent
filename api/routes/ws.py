"""WebSocket 路由：实时事件流（任务/步骤/日志）。"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.context import get_bus

router = APIRouter(tags=["ws"])


@router.websocket("/api/ws")
async def ws_events(websocket: WebSocket) -> None:
    """客户端连接后先发一帧快照，再持续推送事件。"""
    await websocket.accept()
    bus = get_bus()
    queue = bus.subscribe()

    try:
        from api.context import get_log_buffer, get_runner

        # 初始快照：让前端打开页面即恢复当前状态
        snapshot = {"type": "snapshot", "runner": get_runner().snapshot()}
        snapshot["runner"]["recent_logs"] = get_log_buffer().recent(limit=50)
        await websocket.send_json(snapshot)

        while True:
            event = await queue.get()
            await websocket.send_json(event)
    except WebSocketDisconnect:
        pass
    finally:
        bus.unsubscribe(queue)
        # 消费掉队列中残留事件，防止协程泄漏告警
        while not queue.empty():
            queue.get_nowait()
            await asyncio.sleep(0)
