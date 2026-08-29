"""API DTO：与 webagent.core.schemas 解耦，api_key 永不返回明文。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

# ---------- 任务 ----------

class TaskCreateRequest(BaseModel):
    instruction: str = Field(min_length=1, max_length=2000, description="自然语言任务指令")


class TaskOut(BaseModel):
    id: str
    instruction: str
    status: str
    max_steps: int
    created_at: datetime
    finished_at: datetime | None = None


class StepOut(BaseModel):
    step_index: int
    action: dict[str, Any]
    success: bool
    error: str | None = None
    screenshot_url: str | None = None
    created_at: datetime


class TaskDetailOut(BaseModel):
    task: TaskOut
    steps: list[StepOut]


class RunnerStateOut(BaseModel):
    running: bool
    instruction: str
    task_id: str | None
    status: str
    phase: str | None = None


# ---------- 配置 ----------

class LLMConfigOut(BaseModel):
    base_url: str
    api_key: str  # 遮蔽值，形如 ****abcd
    has_api_key: bool
    model: str
    temperature: float
    timeout: int
    max_retries: int


class BrowserConfigOut(BaseModel):
    mode: Literal["launch", "cdp"]
    cdp_url: str
    headless: bool
    viewport_width: int
    viewport_height: int
    user_agent: str | None
    auto_focus_window: bool


class AgentConfigOut(BaseModel):
    max_steps: int
    step_interval_ms: int
    dom_max_elements: int
    screenshot_max_edge: int
    action_retry: int


class LogConfigOut(BaseModel):
    level: str
    rotation: str
    retention: str


class ConfigOut(BaseModel):
    llm: LLMConfigOut
    browser: BrowserConfigOut
    agent: AgentConfigOut
    log: LogConfigOut


class LLMConfigIn(BaseModel):
    base_url: str | None = None
    api_key: str | None = None  # 遮蔽值/空值表示不修改
    model: str | None = None
    temperature: float | None = Field(default=None, ge=0, le=2)
    timeout: int | None = Field(default=None, ge=1, le=600)
    max_retries: int | None = Field(default=None, ge=0, le=10)


class BrowserConfigIn(BaseModel):
    mode: Literal["launch", "cdp"] | None = None
    cdp_url: str | None = None
    headless: bool | None = None
    viewport_width: int | None = Field(default=None, ge=320, le=7680)
    viewport_height: int | None = Field(default=None, ge=240, le=4320)
    user_agent: str | None = None
    auto_focus_window: bool | None = None


class AgentConfigIn(BaseModel):
    max_steps: int | None = Field(default=None, ge=1, le=200)
    step_interval_ms: int | None = Field(default=None, ge=0, le=60000)
    dom_max_elements: int | None = Field(default=None, ge=10, le=500)
    screenshot_max_edge: int | None = Field(default=None, ge=320, le=4096)
    action_retry: int | None = Field(default=None, ge=0, le=10)


class LogConfigIn(BaseModel):
    level: Literal["INFO", "DEBUG", "WARNING", "ERROR", "CRITICAL"] | None = None
    rotation: str | None = None
    retention: str | None = None


class ConfigUpdateRequest(BaseModel):
    llm: LLMConfigIn | None = None
    browser: BrowserConfigIn | None = None
    agent: AgentConfigIn | None = None
    log: LogConfigIn | None = None


# ---------- 日志 ----------

class LogEntryOut(BaseModel):
    time: str
    level: str
    source: str
    message: str


class LogListOut(BaseModel):
    entries: list[LogEntryOut]
