from __future__ import annotations  # 开启注释解析

import sys
from loguru import logger

from webagent.core.config import LOG_DIR, get_settings

_INITIALIZED: bool = False  # 防止重复配置


def init_logger() -> "logger":
    global _INITIALIZED
    if _INITIALIZED:
        return logger

    settings = get_settings()
    logger.remove()

    # 控制台的输出
    logger.add(
        sys.stderr,
        level=settings.log.level,
        format=(
            "<green>{time:HH:mm:ss.SSS}</green> | "
            "<level>{level: <7}</level> | "
            "<cyan>{name}:{function}:{line}</cyan> - <level>{message}</level>"
        ),
        enqueue=False,
        backtrace=False,
        diagnose=False,
    )
    # 文件输出
    logger.add(
        LOG_DIR / "webagent_{time:YYYYMMDD}.log",
        level=settings.log.level,
        rotation=settings.log.rotation,
        retention=settings.log.retention,
        encoding="utf-8",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <7} | {name}:{function}:{line} - {message}",
        enqueue=True,  # 异步写入，不要阻塞主线程
    )

    _INITIALIZED = True
    return logger
