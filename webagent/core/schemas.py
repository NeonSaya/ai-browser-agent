from __future__ import annotations
from datetime import datetime

from typing import Any,Literal
from enum import Enum
from pydantic import BaseModel,Field

# 1.action协议（ai输出->执行器输入）
ActionType=Literal[
    "click",
    "input",
    "goto",
    "press_key",
    "wait",
    "scroll",
    "back",
    "refresh",
    "done",
    "error"
]

class Action(BaseModel):
    '''ai强制输出的标准json动作'''
    action_type: ActionType
    dom_selector: str | None = None
    screen_x:int |None=None
    screen_y:int |None=None
    input_text:str |None=None
    url:str |None=None
    wait_sec:float |None=None
    key:str |None=None
    scroll_delta:int |None=None #上负下正
    reason:str=""

    def is_terminal(self)->bool:
        return self.action_type in ("done","error")


# 2.感知层结构

class DomElement(BaseModel):
    '''dom元素结构''' 
    index:int
    tag:str
    text:str=""
    selector:str
    role:str |None=None #元素的类型
    name:str |None=None #元素的名字
    bbox:tuple[int,int,int,int] | None=None  #[x,y,w,h]屏幕坐标

class PageSnapshot(BaseModel):
    '''单次感知产出的页面快照'''
    url:str=""
    title:str=""
    text_summary:str=""
    elements:list[DomElement]=Field(default_factory=list)
    screen_bs64:str=""
    viewport:tuple[int,int]=(0,0)
    captured_at:datetime=Field(default_factory=datetime.now)

# 3.任务/步骤
class TaskStatus(str,Enum):
    PENDING="pending"
    RUNNING="running"
    DONE="done"
    FAILED="failed"
    CANCELLED="cancelled"

class Task(BaseModel):
    '''用户输入的自然语言任务对象'''
    id:str
    instruction:str
    max_steps:int=15
    success_criteria:str=""
    status:TaskStatus=TaskStatus.PENDING
    created_at:datetime=Field(default_factory=datetime.now)

class StepRecord(BaseModel):
    '''一次[感知-推理-执行]循环的步骤记录'''
    task_id:str
    step_index:int
    action:Action
    success:bool
    error:str|None=None
    screenshot_path:str|None=None
    extra:dict[str,Any]=Field(default_factory=dict)
    
