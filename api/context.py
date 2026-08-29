"""进程级单例：EventBus / LogBuffer / AgentRunner。

独立成模块以避免 routes -> app 的循环导入；
app lifespan 启动时负责 bind_loop 与日志 sink 注册。
"""

from __future__ import annotations

from api.events import EventBus
from api.logbuffer import LogBuffer
from api.runtime import AgentRunner

bus = EventBus()
log_buffer = LogBuffer(bus)


def get_bus() -> EventBus:
    return bus


def get_log_buffer() -> LogBuffer:
    return log_buffer


runner = AgentRunner(bus)


def get_runner() -> AgentRunner:
    return runner
