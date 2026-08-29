"""日志内存环形缓冲：作为 loguru sink，供 /api/logs 与 WS log 事件消费。"""

from __future__ import annotations

from collections import deque
from typing import Any

from api.events import EventBus


class LogBuffer:
    """loguru sink：每条日志进入环形缓冲，并经 EventBus 实时推送。"""

    def __init__(self, bus: EventBus, maxlen: int = 500) -> None:
        self._bus = bus
        self._entries: deque[dict[str, Any]] = deque(maxlen=maxlen)

    def __call__(self, message: Any) -> None:  # loguru sink 协议
        record = message.record
        entry = {
            "time": record["time"].strftime("%H:%M:%S.%f")[:-3],
            "level": record["level"].name,
            "source": f"{record['name']}:{record['function']}:{record['line']}",
            "message": record["message"],
        }
        self._entries.append(entry)
        self._bus.publish({"type": "log", **entry})

    def recent(self, limit: int = 200) -> list[dict[str, Any]]:
        if limit <= 0:
            return []
        entries = list(self._entries)
        return entries[-limit:]
