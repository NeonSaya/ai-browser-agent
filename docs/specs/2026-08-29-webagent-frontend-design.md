# WebAgent 桌面产品 Demo — 前端与打包设计

日期：2026-08-29
状态：已确认

## 目标

在现有 `webagent/` 核心引擎之上，构建一个可直接分发的桌面产品 Demo：

- 前端：React 18 + TypeScript + Vite，四页（监控 / 历史 / 日志 / 设置）
- 通信：FastAPI REST + WebSocket，前后端严格隔离
- 桌面壳：pywebview（Windows WebView2）
- 打包：PyInstaller onedir all-in-one（含 Playwright Chromium 浏览器）
- 隐私：api_key 永不出现在 API 响应中；`.env` 不进 Git

## 三层隔离架构

```
┌──────────────────────────────────────────────┐
│                 EXE (PyInstaller onedir)      │
│  ┌───────────┐  localhost   ┌─────────────┐  │
│  │ pywebview │◄──HTTP/WS───►│  api/        │  │
│  │  窗口壳    │  127.0.0.1  │  FastAPI     │  │
│  └───────────┘              └──────┬──────┘  │
│   React 18 + TS                    │ import  │
│   frontend/ (构建静态资源)          ▼         │
│                             ┌─────────────┐  │
│                             │  webagent/   │  │
│                             │  核心引擎    │  │
│                             └─────────────┘  │
└──────────────────────────────────────────────┘
```

- 依赖方向单向：`api → webagent`；`frontend` 仅通过 HTTP/WS 访问 `api`
- `api/` 拥有独立 DTO（`api/schemas.py`），不把 Pydantic 内部模型直接暴露给前端

## API 设计

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/api/health` | 存活 + 当前运行中任务状态 |
| POST | `/api/tasks` | 创建并启动任务；已有任务运行中返回 409 |
| GET | `/api/tasks` | 任务历史列表 |
| GET | `/api/tasks/{id}` | 任务详情 + 步骤列表 |
| POST | `/api/tasks/{id}/cancel` | 取消（cancel_event） |
| GET | `/api/config` | 配置读取（api_key 遮蔽） |
| PUT | `/api/config` | 配置保存（写 `.env`，清缓存，下个任务生效） |
| WS | `/api/ws` | 事件推送：`task_started` / `step_recorded` / `task_finished` / `log` |

## 线程模型

- `AgentRunner` 单例：同一时间仅一个任务（串行），`threading.Thread` 执行阻塞的 `AgentLoop.run()`
- `on_step` 回调 → 线程安全队列 → asyncio 侧广播给所有 WS 客户端
- 取消：REST 置 `cancel_event`，AgentLoop 在循环内检查点退出

## 配置页与隐私

- `GET /api/config` 返回遮蔽 api_key（`sk-****abcd`）；PUT 时未修改（为空/遮蔽值）则不覆盖
- 配置写入 EXE 同目录 `.env`；保存后 `get_settings.cache_clear()`，AgentRunner 每次新建 AgentLoop 天然热生效
- 打包模式（`sys.frozen`）：数据根目录 = EXE 所在目录，`.env`/`data`/`logs`/`screenshots` 全部本地化

## 日志页

- loguru 追加内存环形缓冲 sink（`deque(maxlen=500)`）
- 复用 `/api/ws` 推送 `log` 事件；日志页实时滚动渲染
- 文件日志（rotation/retention）保持原逻辑不变

## 打包（all-in-one）

- PyInstaller **onedir**（onefile 需解压 ~500MB 至临时目录，启动极慢，不采用）
- 构建脚本自动 `playwright install chromium` → 浏览器二进制打入产物
- 入口 `api/desktop.py`：设 `PLAYWRIGHT_BROWSERS_PATH` 指向包内浏览器目录 → 后台线程启动 uvicorn（随机端口）→ pywebview 窗口加载
- 产物约 500-700MB；后续可选 Inno Setup 压成单安装器（不在本次范围）

## 前端页面

| 页面 | 功能 |
|---|---|
| 监控（默认） | 指令输入 → 创建任务 → 状态徽章（perceiving→reasoning→executing→checking）→ 步骤时间线 → 截图预览 → 取消 |
| 历史 | 任务卡片列表 → 步骤详情与截图回放 |
| 日志 | 实时日志滚动 |
| 设置 | LLM / 浏览器 / Agent 参数编辑，api_key 遮蔽显示 |

技术约束：React Router + 原生 fetch + WebSocket；不引重型状态库；TS strict。

## 代码清理（传 GitHub 前）

1. 删 `main.py` 误导入（`math.log`、`turtle.settiltangle`）
2. 删 `collector.py` 误导入（`tracemalloc.Snapshot`）
3. 修 `test_schema.py` 无效字段 `screen_bs64 → screenshot_bs64`
4. 删 `browser.py` 不可达 return
5. 移除未用依赖：`customtkinter`（被 React 替代）、`langchain`、`langchain-core`、`httpx`
6. `.gitignore` 补：`node_modules/`、`frontend/dist/`、`data/`、`logs/`、`screenshots/`、`build/`、`dist/`、`release/`

## 验证标准

1. `uv run uvicorn api.app:app` 启动 → REST/WS 全部可用
2. `frontend/ npm run build` 通过 TS 严格检查
3. 前端页面走通：创建任务 → 实时监控 → 历史回看 → 配置保存 → 日志滚动
4. `python build_exe.py` 产出 onedir EXE，可双击运行
