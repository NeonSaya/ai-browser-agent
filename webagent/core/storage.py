from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Text,
    JSON,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from webagent.core.config import DATA_DIR

# 数据库配置:创建数据库-连接数据库-构建会话-操作数据库CRUD

DB_PATH = DATA_DIR / "webagent.sqlite"
ENGINE = create_engine(f"sqlite:///{DB_PATH}", future=True)
SessionLocal = sessionmaker(bind=ENGINE, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


class TaskRow(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    instruction: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    max_steps: Mapped[int] = mapped_column(Integer, default=25)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class StepRow(Base):
    __tablename__ = "steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(64), index=True)
    step_index: Mapped[int] = mapped_column(Integer)
    action_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    success: Mapped[bool]
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    screenshot_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


def init_db():
    Base.metadata.create_all(ENGINE)
