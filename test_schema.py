from webagent.core.schemas import (
    Action,
    PageSnapshot,
    TaskStatus,
    Task,
    DomElement,
    StepRecord,
)
from datetime import datetime

a = Action(action_type="click", dom_selector="[data-wa-id='3']", reason="点击搜素按钮")
print(f"action_type{a.action_type},terminal={a.is_terminal()}")


a1 = Action(action_type="done", dom_selector="[data-wa-id='10']", reason="完成搜素")
print(f"action_type{a1.action_type},terminal={a1.is_terminal()}")

b = PageSnapshot(
    url="https://www.baidu.com",
    title="百度一下，你就知道",
    text_summary="这是一个百度搜索页面",
    elements=[DomElement(index=0, tag="div", text="这是一个div", selector="div")],
    screen_bs64="base64编码的图片",
    viewport=(1920, 1080),
    captured_at=datetime.now(),
)
print(f"page_snapshot.elements:{b.elements}")

c = Task(
    id="123",
    instruction="搜索python",
    max_steps=15,
    success_criteria="搜索结果中包含python",
    status=TaskStatus.PENDING,
    created_at=datetime.now(),
)
print(f"success_criteria:{c.success_criteria}")

d = DomElement(
    index=0,
    tag="div",
    text="这是一个div",
    selector="div",
)
print(f"tag:{d.tag},text:{d.text}")

e = StepRecord(
    task_id="123",
    step_index=0,
    action=a,
    success=True,
)
print(f"success:{e.success}")
