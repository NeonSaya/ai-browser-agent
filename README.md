# ai-browser-agent

> A multimodal AI browser agent that autonomously plans and executes web tasks via a perception-reasoning-action loop, powered by Playwright + LLM.

自然语言驱动的 AI 浏览器自动化（RPA）桌面应用。输入一句指令，Agent 自动控制浏览器完成任务，并提供实时监控、历史回溯、日志查看与配置管理。

## 特性

- 🧠 **感知-推理-执行** 状态机循环：DOM 感知 + 页面截图 → 多模态模型决策 → Playwright 执行
- 🖥️ **桌面化**：pywebview 原生窗口 + React 18 前端，打包为 all-in-one EXE（浏览器随包分发）
- 📡 **实时监控**：WebSocket 推送每一步的动作、结果与截图
- 📜 **历史回溯**：任务与步骤持久化，可回看截图
- 🔒 **隐私安全**：API Key 遮蔽显示，永不返回明文；本地数据不进 Git

## 重要：模型要求

本项目的 Agent 依赖**视觉语言模型（VLM）**——感知阶段会把页面截图以 base64 图片形式与 DOM 文本一起发给模型，**模型必须支持图片输入**。

✅ 可用（OpenAI 兼容协议的多模态模型）：

- OpenAI `GPT-4o` / `GPT-4o-mini`
- 阿里云通义千问 `qwen-vl-max` / `qwen-vl-plus`
- DeepSeek `deepseek-vl`（如兼容 OpenAI 协议）

❌ 不可用：纯文本模型（如 `gpt-3.5`、`qwen-turbo`、`deepseek-chat`）——无法接收截图，会导致推理失败。

## 快速开始

### 环境要求

- Python 3.10+（推荐 [uv](https://docs.astral.sh/uv/)）
- Node.js 18+（仅开发/构建时需要）

### 开发模式

```bash
# 1. 安装依赖
uv sync

# 2. 安装浏览器
uv run playwright install chromium

# 3. 配置模型（复制样例并按需修改）
cp .env.example .env

# 4. 启动后端（托管前端）
uv run uvicorn api.app:app --port 8000

# 5. 构建前端
cd frontend && npm install && npm run build
```

访问 http://127.0.0.1:8000

### 打包 EXE

```bash
uv run python scripts/build_exe.py
```

产物为 `dist/WebAgent/WebAgent.exe`（含浏览器，约 500-700MB），双击即用。

## 配置

通过 `.env` 配置，或用应用内「设置」页（API Key 遮蔽保存）。关键项：

```ini
WEBAGENT_LLM__BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
WEBAGENT_LLM__API_KEY=sk-...
WEBAGENT_LLM__MODEL=qwen-vl-max-latest
WEBAGENT_BROWSER__HEADLESS=false
```

完整示例见 [.env.example](.env.example)。

## 架构

```
frontend/   React 18 + TS + Vite（零 Python 依赖，仅 HTTP/WS 通信）
   │  HTTP / WebSocket
api/        FastAPI 层（唯一允许 import webagent 的地方，独立 DTO）
   │  import
webagent/   领域核心（状态机循环 / 感知 / 执行 / 存储）
```

## 项目结构

```
api/               HTTP API 层
frontend/          React 前端（监控 / 历史 / 日志 / 设置）
webagent/          领域核心
  agent/           状态机循环 + VLM 客户端
  perception/      DOM 感知 + 截图
  executor/        Playwright 动作执行
  core/            配置 / 日志 / 存储 / 数据模型
scripts/           构建与测试脚本
```

## 隐私

- API 永不返回明文 `api_key`（只返回 `****后四位`）
- 未修改的 `api_key` 保存时不覆盖
- `.env` / `data/` / `logs/` / `screenshots/` 均在 `.gitignore`
