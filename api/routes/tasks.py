"""任务 REST 路由：创建 / 列表 / 详情 / 取消 / 步骤截图。"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select

from api.context import get_runner
from api.runtime import TaskRunningError
from api.schemas import StepOut, TaskCreateRequest, TaskDetailOut, TaskOut
from webagent.core import repository
from webagent.core.config import SCREENSHOT_DIR
from webagent.core.storage import SessionLocal, StepRow

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.post("", status_code=202)
def create_task(body: TaskCreateRequest) -> dict:
    """创建并启动任务（单任务串行）。"""
    try:
        get_runner().start(body.instruction)
    except TaskRunningError:
        raise HTTPException(status_code=409, detail="已有任务在运行中，请先取消或等待完成") from None
    return {"started": True}


@router.get("", response_model=list[TaskOut])
def list_tasks(limit: int = 100) -> list[TaskOut]:
    limit = max(1, min(limit, 500))
    return [
        TaskOut(
            id=b.id,
            instruction=b.instruction,
            status=b.status,
            max_steps=b.max_steps,
            created_at=b.created_at,
            finished_at=b.finished_at,
        )
        for b in repository.list_tasks(limit=limit)
    ]


@router.post("/current/cancel")
def cancel_current() -> dict:
    """取消当前正在运行的任务。"""
    if not get_runner().cancel():
        raise HTTPException(status_code=409, detail="当前没有正在运行的任务")
    return {"cancelling": True}


@router.get("/{task_id}", response_model=TaskDetailOut)
def get_task(task_id: str) -> TaskDetailOut:
    briefs = {b.id: b for b in repository.list_tasks(limit=500)}
    brief = briefs.get(task_id)
    if brief is None:
        raise HTTPException(status_code=404, detail="任务不存在")

    task = TaskOut(
        id=brief.id,
        instruction=brief.instruction,
        status=brief.status,
        max_steps=brief.max_steps,
        created_at=brief.created_at,
        finished_at=brief.finished_at,
    )
    steps = [
        StepOut(
            step_index=s.step_index,
            action=s.action,
            success=s.success,
            error=s.error,
            screenshot_url=(
                f"/api/tasks/{task_id}/steps/{s.step_index}/screenshot" if s.screenshot_path else None
            ),
            created_at=s.created_at,
        )
        for s in repository.list_steps(task_id)
    ]
    return TaskDetailOut(task=task, steps=steps)


@router.get("/{task_id}/steps/{step_index}/screenshot")
def get_step_screenshot(task_id: str, step_index: int) -> FileResponse:
    """返回步骤截图（仅允许访问 SCREENSHOT_DIR 内的文件）。"""
    with SessionLocal() as session:
        row = session.execute(
            select(StepRow).where(StepRow.task_id == task_id, StepRow.step_index == step_index)
        ).scalar_one_or_none()

    if row is None or not row.screenshot_path:
        raise HTTPException(status_code=404, detail="截图不存在")

    path = Path(row.screenshot_path).resolve()
    if not str(path).startswith(str(SCREENSHOT_DIR.resolve())):
        raise HTTPException(status_code=403, detail="非法路径")

    if not path.is_file():
        raise HTTPException(status_code=404, detail="截图文件已丢失")

    return FileResponse(path, media_type="image/png")
