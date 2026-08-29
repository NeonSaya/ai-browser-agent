'''agent主循环（状态机驱动）'''
from __future__ import annotations

from optparse import Option
import uuid
import threading
import time
from dataclasses import dataclass,field
from datetime import datetime
from pathlib import Path
from typing import Optional,Callable

from sqlalchemy import exc
from transitions import Machine

from webagent.agent.llm_client import VLMClient
from webagent.core.config import SCREENSHOT_DIR, get_settings
from webagent.core.exceptions import AgentLoopError
from webagent.core.logger import init_logger
from webagent.core.schemas import Action, StepRecord, Task, TaskStatus
from webagent.core.storage import SessionLocal, StepRow, TaskRow, init_db 
from webagent.executor.actions import ActionExecutor
from webagent.executor.browser import BrowserManager
from webagent.perception.collector import PerceptionCollector

log = init_logger()

_STATES = ["idle", "perceiving", "reasoning", "executing", "checking", "done", "failed"]

@dataclass
class _LoopContext:
    task: Task
    snapshot: Optional[object] = None
    last_action: Optional[Action] = None
    last_error: Optional[str] = None
    prev_url: Optional[str] = None
    prev_title: Optional[str] = None
    history: list[Action] = field(default_factory=list)
    steps: list[StepRecord] = field(default_factory=list)
    step_index: int = 0
    # 死循环检测
    repeat_count: int = 0
    repeat_key: Optional[tuple] = None

class AgentLoop:
    '''agent自主循环主控'''
    def __init__(
        self,
        on_step:Optional[Callable[[_LoopContext],None]]=None,
        cancel_event:Optional[threading.Event]=None,
    )->None:
        self.cfg=get_settings().agent
        self._on_step=on_step or (lambda _r:None)
        self.cancel_event=cancel_event or threading.Event()

        # 各层组件
        self.browser=BrowserManager()
        self.perception=PerceptionCollector()
        self.llm=VLMClient()
        self.executor: Optional[ActionExecutor]=None
        self.ctx:Optional[_LoopContext]=None

        # 状态机
        self.machine = Machine(
            model=self,
            states=_STATES,
            initial="idle",
            auto_transitions=False, #禁止瞬移
            transitions=[
                {"trigger": "start", "source": "idle", "dest": "perceiving"},
                {"trigger": "perceived", "source": "perceiving", "dest": "reasoning"},
                {"trigger": "decided", "source": "reasoning", "dest": "executing"},
                {"trigger": "executed", "source": "executing", "dest": "checking"},
                {"trigger": "loop", "source": "checking", "dest": "perceiving"},
                {"trigger": "finish_done", "source": "*", "dest": "done"},
                {"trigger": "fail", "source": "*", "dest": "failed"},
            ],
        )

    # 主入口
    def run(self,instruction:str)->Task:
        '''执行一个自然语言任务'''
        init_db()
        task=Task(
            id=str(uuid.uuid4()),
            instruction=instruction,
            max_steps=self.cfg.max_steps,
            status=TaskStatus.RUNNING,
        )
        self.ctx=_LoopContext(task=task)
        self._persist_task(task)
        log.info(f"启动任务 {task.id} | {instruction} ")
        try:
            self.browser.start()
            self.executor=ActionExecutor(self.browser.page)
            self.start()
            self._main_loop()
        except Exception as e:
            log.exception(f"任务异常终止：{e}")
            task.status=TaskStatus.FAILED
            self.fail()
        finally:
            self.browser.stop()
            self._finalize_task(task)
        return task

    # 控制
    def cancel(self)->None:
        '''取消当前任务（线程安全）'''
        log.warning("收到取消请求->正在取消当前任务")
        self.cancel_event.set()

    def _check_cancel(self,ctx:"_LoopContext")->bool:
        if not self.cancel_event.is_set():
            return False
        log.error("任务已被用户取消")
        self._record_step(ctx,Action(action_type="error",reason="用户取消"),False,"cancelled")
        ctx.task.status=TaskStatus.CANCELLED
        try:
            self.fail()
        except Exception:
            pass
        return True

    # 主循环
    def _main_loop(self)->None:
        '''主循环（感知，推理，执行，循环）'''
        assert self.ctx is not None and self.executor is not None
        ctx=self.ctx
        # 只要状态机处于"perceiving","reasoning","executing","checking"状态。就循环
        while self.state in ("perceiving","reasoning","executing","checking"):
            # 检查取消请求
            if self._check_cancel(ctx):
                break
            # 同步拉取当前活动page
            self.executor.page=self.browser.page
            ctx.step_index+=1
            # 防止死循环，设置最大步数限制
            if ctx.step_index>ctx.task.max_steps:
                log.error(f"任务执行超最大步数限制{ctx.task.max_steps}")
                ctx.task.status=TaskStatus.FAILED
                self.fail()
                break

            log.info(f"Step {ctx.step_index} / {ctx.task.max_steps}")

            # 1) 感知: 采集当前页面信息(DOM + 截图)

            try:
                ctx.snapshot=self.perception.capture(self.browser.page)
            except Exception as e:
                self._record_step(ctx,Action(action_type="error",reason=f"感知失败：{e}"),False,str(e))
                ctx.task.status=TaskStatus.FAILED
                self.fail()
                break
            self.perceived() # 触发感知状态机切换 perceiving->reasoning

            # 2）推理：调用ai决策下一步动作

            try:
                action=self.llm.decide(ctx.task,ctx.snapshot,ctx.history,ctx.last_error,ctx.prev_url,ctx.prev_title)
            except Exception as e:
                self._record_step(ctx,Action(action_type="error",reason=f"推理失败：{e}"),False,str(e))
                ctx.task.status=TaskStatus.FAILED
                self.fail()
                break

            ctx.last_action=action
            ctx.history.append(action)
            self.decided() # 触发推理状态机切换 reasoning->executing

            # 3）终态判断：如果ai任务任务已完成或者遇到不可恢复的错误，直接退出

            if action.action_type == "done":
                self._record_step(ctx, action, True)
                ctx.task.status = TaskStatus.DONE
                self.finish_done()
                break
            if action.action_type == "error":
                self._record_step(ctx, action, False, action.reason)
                ctx.task.status = TaskStatus.FAILED
                self.fail()
                break

            # 4）执行：根据ai的决策执行动作，操作浏览器

            try:
                self.executor.execute(action)
                ok,err=True,None
            except Exception as e:
                ok,err=False,str(e)
                log.warning(f"最终执行动作失败：{e}")

            # 5）记录+截图留存：保存每一步的操作记录，方便时候回溯

            screenshot_path=self._save_step_screenshot(ctx)
            record=self._record_step(ctx, action, ok, err, screenshot_path)
            self._on_step(record) #回调函数，用于GUI实施更新步骤面板
            self.executed() # 触发执行状态机切换 executing->checking
            # 死循环检测逻辑，听一个页面连续执行并成功3次，且页面没有变化，说明进入死循环
            cur_url=getattr(ctx.snapshot,"url",None)
            cur_title=getattr(ctx.snapshot,"title",None)
            page_changed=(cur_url!=ctx.prev_url) or (cur_title!=ctx.prev_title)
            cur_key=(action.action_type,action.dom_selector,action.input_text,action.url)

            if ok and not page_changed and cur_key == ctx.repeat_key:
                ctx.repeat_count+=1
            else:
                ctx.repeat_count=1 if ok else 0 #动作不同，页面变了，重置计数器
                ctx.repeat_key=cur_key if ok else None

            if ctx.repeat_count>=3:  #连续3次相同动作且页面不变，判定为死循环
                log.error(
                    "检测到死循环：同动作连续 {} 次执行且页面未变化，终止任务",
                    ctx.repeat_count,
                )
                ctx.task.status=TaskStatus.FAILED
                self.fail()
                break

            # 更新prev_url/prev_title给下一步对比
            ctx.prev_url=cur_url
            ctx.prev_title=cur_title

            # 6）短暂等待：给页面渲染留出时间，同时检查用户是否取消任务

            self.cancel_event.wait(timeout=self.cfg.step_interval_ms / 1000.0)
            if self._check_cancel(ctx):
                break
            self.loop()  # 触发状态机转换成checking->perceiving，开始下一轮循环

    # 辅助函数
    def _save_step_screenshot(self, ctx: _LoopContext) -> Optional[str]:
        try:
            path: Path = SCREENSHOT_DIR / f"{ctx.task.id}_step{ctx.step_index:02d}.png"
            self.browser.page.screenshot(path=str(path), full_page=False)
            return str(path)
        except Exception as e:
            log.debug(f"步骤截图失败（忽略）：{e}")
            return None

    # 持久化
    def _persist_task(self, task: Task) -> None:
        with SessionLocal() as session:
            session.add(
                TaskRow(
                    id=task.id,
                    instruction=task.instruction,
                    status=task.status.value,
                    max_steps=task.max_steps,
                    created_at=task.created_at,
                )
            )
            session.commit()

    def _record_step(
        self,
        ctx: _LoopContext,
        action: Action,
        success: bool,
        error: Optional[str] = None,
        screenshot_path: Optional[str] = None,
    ) -> StepRecord:
        record = StepRecord(
            task_id=ctx.task.id,
            step_index=ctx.step_index,
            action=action,
            success=success,
            error=error,
            screenshot_path=screenshot_path,
        )
        ctx.steps.append(record)
        with SessionLocal() as session:
            session.add(
                StepRow(
                    task_id=record.task_id,
                    step_index=record.step_index,
                    action_json=action.model_dump(exclude_none=True),
                    success=success,
                    error=error,
                    screenshot_path=screenshot_path,
                )
            )
            session.commit()
        return record

    def _finalize_task(self, task: Task) -> None: #归档操作
        with SessionLocal() as session:
            row = session.get(TaskRow, task.id)
            if row is not None:
                row.status = task.status.value
                row.finished_at = datetime.now()
                session.commit()
        log.info(f"任务结束: {task.id} | status={task.status.value}")

def run_task(instruction: str)->Task:
    return AgentLoop().run(instruction)
