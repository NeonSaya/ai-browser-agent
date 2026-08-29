"""取消功能测试：创建任务后 2 秒取消，验证 task_finished(status=cancelled)。"""

import asyncio
import json
import time
import urllib.request

import websockets

BASE = "http://127.0.0.1:8000"
WS = "ws://127.0.0.1:8000/api/ws"


def post(path: str, body: dict | None = None) -> tuple[int, str]:
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(body).encode("utf-8") if body else None,
        headers={"Content-Type": "application/json"} if body else {},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")


async def main() -> None:
    async with websockets.connect(WS) as ws:
        await ws.recv()  # 丢弃 snapshot

        code, body = post("/api/tasks", {"instruction": "打开百度搜索 python 教程，浏览前三个搜索结果"})
        print(f"[POST] create: {code} {body}")

        # 等任务跑出 1-2 步再取消
        steps = 0
        start = time.time()
        while time.time() - start < 15:
            msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=15))
            if msg["type"] == "step_recorded":
                steps += 1
                print(f"[WS] step {msg.get('step_index')}: {msg.get('action', {}).get('action_type')}")
                if steps >= 2:
                    break

        # 取消
        code, body = post("/api/tasks/current/cancel")
        print(f"[POST] cancel: {code} {body}")

        # 观察最终事件
        final = None
        start = time.time()
        while time.time() - start < 30:
            msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=30))
            if msg["type"] == "task_finished":
                final = msg
                break
            if msg["type"] == "step_recorded":
                print(f"[WS] step {msg.get('step_index')}: {msg.get('action', {}).get('action_type')} err={msg.get('error')}")

        print(f"\n[WS] 最终 task_finished: {final}")


if __name__ == "__main__":
    asyncio.run(main())
