"""配置 REST 路由：读取（遮蔽）/ 更新（写入 .env）。"""

from __future__ import annotations

from fastapi import APIRouter

from api import config_io
from api.schemas import ConfigOut, ConfigUpdateRequest

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("", response_model=ConfigOut)
def get_config() -> ConfigOut:
    """读取当前配置（api_key 以遮蔽形式返回）。"""
    return config_io.read_config()


@router.put("", response_model=ConfigOut)
def put_config(req: ConfigUpdateRequest) -> ConfigOut:
    """更新配置并持久化到 .env；下个任务生效。"""
    return config_io.update_config(req)
