from __future__ import annotations  # 开启注释解析

from functools import lru_cache  # 缓存配置加载
from pathlib import Path  # os.path优雅版本
from typing import Literal  # 限制字符串的取值

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

# 在当前目录下加载配置文件，上面两级就是根目录
PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
DATA_DIR: Path = PROJECT_ROOT / "data"
LOG_DIR: Path = PROJECT_ROOT / "logs"
SCREENSHOT_DIR: Path = PROJECT_ROOT / "screenshots"


class LLMSettings(BaseSettings):
    """大模型配置。"""

    base_url: str = "https://token-plan-cn.xiaomimimo.com/v1"
    api_key: str = ""
    model: str = "mimo-v2.5"
    temperature: float = 0.2
    timeout: int = 60
    max_retries: int = 2


class BrowserSettings(BaseSettings):
    """浏览器配置。"""

    mode: Literal["launch", "cdp"] = "launch"
    cdp_url: str = "http://localhost:9222"
    headless: bool = False  # 是否无头模式
    viewport_width: int = 1440  # 视口宽度
    viewport_height: int = 900  # 视口高度
    user_agent: str | None = None  # 为空就是浏览器默认user_agent

    auto_focus_window: bool = True  # 是否自动聚焦窗口


class AgentSettings(BaseSettings):
    """agent配置。"""

    max_steps: int = 25
    step_interval_ms: int = 600  # 每步间隔，单位毫秒，默认600ms
    dom_max_elements: int = 60
    screenshot_max_edge: int = 1280
    action_retry: int = 1  # 单步执行层面：动作重试次数


class LogSetting(BaseSettings):
    """日志配置。"""

    level: Literal["INFO", "DEBUG", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    rotation: str = "10 MB"
    retention: str = "14 days"


class Settings(BaseSettings):
    """根设置对象"""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        env_prefix="WEBAGENT_",
        env_nested_delimiter="__",
        extra="ignore",
    )
    llm: LLMSettings = Field(default_factory=LLMSettings)
    browser: BrowserSettings = Field(default_factory=BrowserSettings)
    agent: AgentSettings = Field(default_factory=AgentSettings)
    log: LogSetting = Field(default_factory=LogSetting)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """全局唯一Setting实例（lru_cache缓存）"""
    for d in (DATA_DIR, LOG_DIR, SCREENSHOT_DIR):
        d.mkdir(parents=True, exist_ok=True)
    return Settings()
