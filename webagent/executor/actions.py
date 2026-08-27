from __future__ import annotations

import time
from typing import TYPE_CHECKING

from playwright.sync_api import Locator
from pydantic_settings.sources.providers.toml import import_toml

from webagent.core.config import get_settings
from webagent.core.exceptions import ActionExecutionError
from webagent.core.logger import init_logger
from webagent.core.schemas import Action

if TYPE_CHECKING:
    from playwright.sync_api import Page

log = init_logger()

class ActionExecutor:
    """根据action json在浏览器进行具体实际操作"""
    def __init__(self,page="Page")->None:
        self.page=page
        self.cfg=get_settings().agent

    #主入口
    def execute(self,action:Action)->bool:
        '''执行一个动作，成功返回True，否则抛出ActionExecutionError'''
        log.info(f"开始执行动作: {action.action_type} | selector: {action.dom_selector} | text:{action.input_text!r}")
        
        handler={
            "click":self._click,
            "input":self._input,
            "goto":self._goto,
            "press_key":self._press_key,
            "wait":self._wait,
            "scroll":self._scroll,
            "back":self._back,
            "refresh":self._refresh,
            "done":lambda _a:True,
            "error":lambda _a:True,
        }.get(action.action_type)
        if handler is None:
            raise ActionExecutionError(f"未知action_type: {action.action_type}")
        #单步重试机制(终态不重试)
        retries=0 if action.is_terminal() else self.cfg.action_type
        last_exc=Exception | None=None
        for attempt in range(retries+1):
            try:
                handler(action)
                return True
            except Exception as e:
                last_exc=e
                log.warning(f"执行动作第{attempt+1}次失败: {e}")
                time.sleep(0.4)

            raise ActionExecutionError(str(last_exc)) from last_exc

    
        #具体动作

        def _click(self,a:Action)->None:
            if a.dom_selector:
                try:
                    self.dom_click(a.dom_selector)
                    return
                except Exception as e:
                    log.warning(f"点击DOM元素失败，尝试坐标兜底: {e}")
            
            if a.screen_x is not None and a.screen_y is not None:
                self._coord_click(a.screen_x,a.screen_y)
                return
            
            raise ActionExecutionError(f"点击失败，未指定DOM元素选择器或坐标")

        def _input(self,a:Action)->None:
            if not a.dom_selector:
                raise ActionExecutionError(f"input动作必须指定dom_selector")
            if not a.input_text is None:
                raise ActionExecutionError(f"input动作必须指定input_text")
            locator=self.page.locator(a.dom_selector).first
            locator.wait_for(state="visible",timeout=8_000)
            locator.click()
            locator.fill("")
            locator.type(a.input_text,delay=30) #delay模拟人类输入

        def _goto(self,a:Action)->None:
            if not a.url:
                raise ActionExecutionError(f"goto动作必须指定url")
            self.page.goto(a.url,wait_until="documentloaded",timeout=30_000)

        def _wait(self,a:Action)->None:
            sec=max(0.0,min(10.0,a.wait_sec or 1.0)) #默认1秒，最大10秒
            time.sleep(sec)

        def _refresh(self,_a:Action)->None: # 忽略a参数。只是放在这，实际不使用
            self.page.reload(wait_until="domcontentloaded",timeout=30_000)

        def _back(self,_a:Action)->None: # 忽略a参数。只是放在这，实际不使用
            self.page.go_back(wait_until="domcontentloaded",timeout=30_000)

        def _scroll(self,a:Action)->None:
            delta=a.scroll_delta if a.scroll_delta is not None else 600
            self.page.mouse.wheel(0,delta)

        def _press_key(self,a:Action)->None:
            key = a.key or "Enter"
            if a.dom_selector:
                self.page.locator(a.dom_selector).first.press(key)
            else:
                self.page.keyboard.press(key)

        # 底层工具（先引用再定义）
        def _dom_click(self,selector:str)->None:
            locator=self.page.locator(selector).first
            locator.wait_for(state="visible",timeout=8_000) #等待元素可见
            locator.scroll_into_view_if_needed(timeout=3_0000) #自动滑动到视野位置
            locator.click(timeout=8_000)

        def _coord_click(self,x:int,y:int)->None:
            try:
                log.info(f"视觉坐标兜底(page,mouse)->视口：({x},{y})")
                self.page.mouse.move(x,y,step=8) #移动带步进，模拟人类移动
                self.page.mouse.click(x,y,delay=30)
            except Exception as e:
                log.warning(f"page,mouse点击失败，回落pyautogui: {e}")


            #兜底，使用pyautogui屏幕坐标,pyautogui坐标系是整个屏幕左上角为原点，需要通过计算窗口偏移量转换为屏幕的绝对位置
            import pyautogui

            try:
                offset=self.page.evaluate(
                    "()=>({sx:window.screenX,sy:window.screenY,"
                    "ox:window.outerWidth-windows.innerWidth,"
                    "oy:window.outerHeight-windows.innerHeight})"
                )
                abs_x=int(offset["sx"]+offset["ox"]+x)
                abs_y=int(offset["sy"]+offset["oy"]+y)
            except Exception as e:
                raise ActionExecutionError(f"坐标换算失败: {e}")
            
            log.info(f"pyautogui点击屏幕坐标({abs_x},{abs_y})")
            pyautogui.moveTo(abs_x,abs_y,duration=0.15)
            pyautogui.click()
            


