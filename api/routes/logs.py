"""日志 REST 路由：拉取内存环形缓冲中的最近日志。"""

from __future__ import annotations

from fastapi import APIRouter, Query

from api.context import get_log_buffer
from api.schemas import LogEntryOut, LogListOut

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("", response_model=LogListOut)
def get_logs(limit: int = Query(default=200, ge=1, le=500)) -> LogListOut:
    entries = [
        LogEntryOut(time=e["time"], level=e["level"], source=e["source"], message=e["message"])
        for e in get_log_buffer().recent(limit=limit)
    ]
    return LogListOut(entries=entries)
