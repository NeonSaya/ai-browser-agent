"""api 包：WebAgent 的 HTTP API 层。

架构约定（见 docs/specs/2026-08-29-webagent-frontend-design.md）：
- 本包是唯一允许 import webagent 的地方
- 前端（frontend/）零 Python 依赖，仅通过 HTTP/WebSocket 与本层通信
"""

from api.app import create_app

__all__ = ["create_app"]
