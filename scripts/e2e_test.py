"""端到端测试：连接 WS 监听事件，同时创建真实任务，验证完整数据链路。

用法：uv run python scripts/e2e_test.py
"""

import asyncio
import json
import time
import urllib.request

import websockets

BASE = "http://127.0.0.1:8000"
WS = "ws://127.0.0.1:8000/api/ws"


def post_task(instruction: str) -> tuple[int, str]:
    req = urllib.request.Request(
        f"{BASE}/api/tasks",
        data=json.dumps({"instruction": instruction}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")


async def main() -> None:
    events: list[dict] = []
    async with websockets.connect(WS) as ws:
        snapshot = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
        runner = snapshot.get("runner", {})
        print(f"[WS] snapshot: type={snapshot.get('type')} running={runner.get('running')}")

        instruction = "打开必应搜索 hello world"
        code, body = post_task(instruction)
        print(f"[POST] create task: {code} {body}")

        started = time.time()
        timeout = 180
        try:
            while time.time() - started < timeout:
                msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=timeout))
                events.append(msg)
                t = msg.get("type")
                if t == "step_recorded":
                    action = msg.get("action", {})
                    print(
                        f"[WS] step: idx={msg.get('step_index')} action={action.get('action_type')} "
                        f"success={msg.get('success')} err={msg.get('error')}"
                    )
                elif t == "task_finished":
                    print(f"[WS] task_finished: status={msg.get('status')} error={msg.get('error')}")
                    break
                elif t == "task_started":
                    print(f"[WS] task_started: {msg.get('instruction')}")
        except asyncio.TimeoutError:
            print("[WS] 超时：未收到 task_finished")

    step_events = [e for e in events if e["type"] == "step_recorded"]
    print(f"\n共收到 {len(events)} 个事件，其中步骤事件 {len(step_events)} 个")


if __name__ == "__main__":
    asyncio.run(main())
