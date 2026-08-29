"""配置读写：.env 持久化 + api_key 遮蔽。

隐私约定：
- GET 永不返回明文 api_key，只返回遮蔽值（****后4位）
- PUT 提交空值或遮蔽值时，视为"未修改"，不覆盖已保存的 key
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from api.schemas import (
    ConfigOut,
    ConfigUpdateRequest,
)
from webagent.core.config import PROJECT_ROOT, get_settings

ENV_PATH: Path = PROJECT_ROOT / ".env"


def mask_key(key: str) -> str:
    """把 api_key 转为遮蔽形式。"""
    if not key:
        return ""
    tail = key[-4:] if len(key) >= 4 else key
    return f"****{tail}"


def _is_masked_or_empty(value: str | None) -> bool:
    if value is None:
        return True
    value = value.strip()
    return value == "" or value.startswith("****")


def read_config() -> ConfigOut:
    """读取当前配置（api_key 遮蔽）。"""
    s = get_settings()
    return ConfigOut(
        llm={
            "base_url": s.llm.base_url,
            "api_key": mask_key(s.llm.api_key),
            "has_api_key": bool(s.llm.api_key),
            "model": s.llm.model,
            "temperature": s.llm.temperature,
            "timeout": s.llm.timeout,
            "max_retries": s.llm.max_retries,
        },
        browser=s.browser.model_dump(),
        agent=s.agent.model_dump(),
        log=s.log.model_dump(),
    )


def update_config(req: ConfigUpdateRequest) -> ConfigOut:
    """写入 .env 并刷新配置缓存；返回更新后的配置（遮蔽）。"""
    updates: dict[str, str | None] = {}

    if req.llm is not None:
        llm_data = req.llm.model_dump(exclude_unset=True)
        if _is_masked_or_empty(llm_data.get("api_key")):
            llm_data.pop("api_key", None)  # 未修改：不覆盖已保存的 key
        updates.update(_flatten("WEBAGENT_LLM", llm_data))
    if req.browser is not None:
        updates.update(_flatten("WEBAGENT_BROWSER", req.browser.model_dump(exclude_unset=True)))
    if req.agent is not None:
        updates.update(_flatten("WEBAGENT_AGENT", req.agent.model_dump(exclude_unset=True)))
    if req.log is not None:
        updates.update(_flatten("WEBAGENT_LOG", req.log.model_dump(exclude_unset=True)))

    if updates:
        _write_env(updates)
        get_settings.cache_clear()

    return read_config()


def _flatten(prefix: str, data: dict[str, Any]) -> dict[str, str | None]:
    """把嵌套 dict 展平为 WEBAGENT_ 前缀的环境变量名。"""
    result: dict[str, str | None] = {}
    for key, value in data.items():
        env_key = f"{prefix}__{key.upper()}"
        if value is None or value == "":
            result[env_key] = None  # 删除该行，回落到默认值
        elif isinstance(value, bool):
            result[env_key] = "true" if value else "false"
        else:
            result[env_key] = str(value)
    return result


def _write_env(updates: dict[str, str | None]) -> None:
    """更新 .env：只改动本次提交的键，保留文件中的其他内容。"""
    existing: dict[str, str] = {}
    other_lines: list[str] = []

    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                other_lines.append(line)
                continue
            key, _, value = stripped.partition("=")
            existing[key.strip()] = value

    for key, value in updates.items():
        if value is None:
            existing.pop(key, None)
        else:
            existing[key] = value

    lines = list(other_lines)
    lines.extend(f"{key}={value}" for key, value in existing.items())
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
