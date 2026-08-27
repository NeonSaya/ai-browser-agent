from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import select

from webagent.core.storage import SessionLocal, StepRow, TaskRow


@dataclass
class TaskBrief:
    id: str
    instruction: str
    status: str
    max_steps: int
    created_at: datetime
    finished_at: datetime | None


@dataclass
class StepBrief:
    step_index: int
    action: dict[str, Any]
    success: bool
    error: str | None
    screenshot_path: str | None
    created_at: datetime


def list_tasks(limit: int = 100) -> list[TaskBrief]:
    with SessionLocal() as session:
        rows = (
            session.execute(
                select(TaskRow).order_by(TaskRow.created_at.desc()).limit(limit)
            )
            .scalars()
            .all()
        )
        return [
            TaskBrief(
                id=r.id,
                instruction=r.instruction,
                status=r.status,
                max_steps=r.max_steps,
                created_at=r.created_at,
                finished_at=r.finished_at,
            )
            for r in rows
        ]


def list_steps(task_id: str) -> list[StepBrief]:
    """拉取某任务的全部步骤。"""
    with SessionLocal() as session:
        rows = (
            session.execute(
                select(StepRow)
                .where(StepRow.task_id == task_id)
                .order_by(StepRow.step_index.asc())
            )
            .scalars()
            .all()
        )
        return [
            StepBrief(
                step_index=r.step_index,
                action=r.action_json or {},
                success=r.success,
                error=r.error,
                screenshot_path=r.screenshot_path,
                created_at=r.created_at,
            )
            for r in rows
        ]
