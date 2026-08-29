"""健康检查路由：返回 AgentRunner 当前运行状态。"""

from __future__ import annotations

from fastapi import APIRouter

from api.context import get_runner
from api.schemas import RunnerStateOut

router = APIRouter(tags=["health"])


@router.get("/api/health", response_model=RunnerStateOut)
def health() -> RunnerStateOut:
    return RunnerStateOut(**get_runner().snapshot())
