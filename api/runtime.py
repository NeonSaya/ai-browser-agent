"""AgentRunner：后台线程驱动 AgentLoop，把执行过程桥接为 WS 事件。

单任务串行：同一时间最多一个任务在运行（Playwright 单实例约束）。
"""

from __future__ import annotations

import threading
from typing import Any

from loguru import logger

from api.events import EventBus
from webagent.agent.loop import AgentLoop
from webagent.core.schemas import StepRecord


class TaskRunningError(RuntimeError):
    """已有任务在运行中。"""


class AgentRunner:
    def __init__(self, bus: EventBus) -> None:
        self._bus = bus
        self._thread: threading.Thread | None = None
        self._cancel_event = threading.Event()
        self._loop: AgentLoop | None = None
        self._instruction: str = ""
        self._task_id: str | None = None
        self._status: str = "idle"  # idle / running / done / failed / cancelled

    # ---------- 状态查询 ----------

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def snapshot(self) -> dict[str, Any]:
        """当前运行状态（供 health / WS 初始快照）。"""
        phase = None
        if self.is_running and self._loop is not None:
            try:
                phase = self._loop.state  # 状态机当前相位
            except Exception:  # noqa: BLE001 状态机未启动时读取 state 可能抛异常，容忍
                phase = None
        return {
            "running": self.is_running,
            "instruction": self._instruction,
            "task_id": self._task_id,
            "status": self._status,
            "phase": phase,
        }

    # ---------- 任务控制 ----------

    def start(self, instruction: str) -> None:
        if self.is_running:
            raise TaskRunningError("已有任务在运行中，请先取消或等待完成")

        instruction = instruction.strip()
        if not instruction:
            raise ValueError("任务指令不能为空")

        self._instruction = instruction
        self._task_id = None
        self._status = "running"
        self._cancel_event = threading.Event()
        self._thread = threading.Thread(
            target=self._worker, args=(instruction,), name="agent-runner", daemon=True
        )
        self._thread.start()

    def cancel(self) -> bool:
        """请求取消当前任务（线程安全，实际退出在 AgentLoop 检查点完成）。"""
        if not self.is_running:
            return False
        logger.warning("API 收到取消请求")
        self._cancel_event.set()
        return True

    # ---------- 内部实现 ----------

    def _worker(self, instruction: str) -> None:
        self._bus.publish({"type": "task_started", "instruction": instruction})
        try:
            # 每个任务新建 AgentLoop：配置热更新在下个任务生效
            loop = AgentLoop(on_step=self._on_step, cancel_event=self._cancel_event)
            self._loop = loop
            task = loop.run(instruction)
            self._task_id = task.id
            self._status = task.status.value
            self._bus.publish(
                {"type": "task_finished", "task_id": task.id, "status": task.status.value}
            )
        except Exception as exc:  # noqa: BLE001 兜底：保证前端一定能收到结束事件
            logger.exception(f"任务线程异常终止：{exc}")
            self._status = "failed"
            self._bus.publish(
                {
                    "type": "task_finished",
                    "task_id": self._task_id,
                    "status": "failed",
                    "error": str(exc),
                }
            )
        finally:
            self._loop = None

    def _on_step(self, record: StepRecord) -> None:
        """AgentLoop 预留的 on_step 回调（工作线程中执行）。"""
        self._task_id = record.task_id
        self._bus.publish(
            {
                "type": "step_recorded",
                "task_id": record.task_id,
                "step_index": record.step_index,
                "action": record.action.model_dump(exclude_none=True),
                "success": record.success,
                "error": record.error,
                "screenshot_url": (
                    f"/api/tasks/{record.task_id}/steps/{record.step_index}/screenshot"
                    if record.screenshot_path
                    else None
                ),
            }
        )
