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
        self.executor=Optional[ActionExecutor]=None
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

    #主入口
    def run(self,instruction:str)->Task:
        '''执行一个自然语言任务'''
        init_db()
        task=Task(
            id=uuid.uuid4(),
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
