from __future__ import annotations
from re import S
import time
from typing import Optional

from playwright.sync_api import (
    Browser, BrowserContext, Page, Playwright, sync_playwright,
)
from playwright_stealth import Stealth

from webagent.core.config import get_settings
from webagent.core.exceptions import BrowserError
from webagent.core.logger import init_logger


log=init_logger()

# 模拟一个真实的user_agent
_DEFAULT_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36 Edg/151.0.0.0"

class BrowserManager:
    '''playwright浏览器统一封装'''
    def __init__(self):
        self.settings = get_settings().browser
        self._pw:Optional[Playwright]=None
        self._browser:Optional[Browser]=None
        self._context:Optional[BrowserContext]=None
        self._page:Optional[Page]=None
        
        #生命周期
    def start(self)->Page:
        '''启动浏览器，返回当前活动page'''
        if self._page is not None:
            return self._page
        log.info(f"启动浏览器,模式:{self.settings.mode}...")
        self._pw=sync_playwright().start()
        try:
            if self.settings.mode=='cdp':
                self._start_cdp()
            else:
                self._start_launch()

        except Exception as e:
            self.stop()
            raise BrowserError(f"启动浏览器失败: {e}") from e

        assert self._page is not None
        vp=self._page.viewport_size or {'width':0,'height':0}
        log.success(f"浏览器启动成功,窗口大小:{vp['width']}x{vp['height']}")

        if self.settings.auto_focus_window:
            try:
                self.focus_windows()
            except Exception as e:
                log.warning(f"自动聚焦窗口失败: {e}")

        return self._page

    def stop(self)->None:
        '''停止浏览器并释放资源'''
        try:
            if self._context is not None:
                self._context.close()
        except Exception:
            pass
        try:
            if self._browser is not None:
                self._browser.close()
        except Exception:
            pass
        try:
            if self._pw is not None:
                self._pw.stop()
        except Exception:
            pass

        self._page=None
        self._context=None
        self._browser=None
        self._pw=None

 
# 启动策略
    def _start_launch(self)->None:
        '''启动launch模式，并启动stealth'''
        assert self._pw is not None
        self._browser=self._pw.chromium.launch(
            headless=self.settings.headless,
            args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-default-browser-check",
                    "--disable-infoobars",
                    "--start-maximized",
            ]
        )
        self._context=self._browser.new_context(
            viewport={
                "width":self.settings.viewport_width,
                "height":self.settings.viewport_height,
            },
            user_agent= self.settings.user_agent or _DEFAULT_UA,
            locale='zh-CN',
            timezone_id='Asia/Shanghai',
        )
        #应用stealth，抹掉常见自动化指纹
        Stealth().apply_stealth_sync(self._context)
        self._page=self._context.new_page()

        
    def _start_cdp(self)->None:
        '''cdp模式接管'''
        assert self._pw is not None
        self._browser=self._pw.chromium.connect_over_cdp(
            url=self.settings.cdp_url,
        )
        if not self._browser.contexts():
            raise BrowserError("CDP连接失败")
        self._context=self._browser.contexts()[0]
        self._page=self._context.new_page()
        if self._context.pages:
            self._page=self._context.pages[0]
        else:
            self._page=self._context.new_page()
        try:
            Stealth().apply_stealth_sync(self._context)
        except Exception as e:
            log.debug(f"CDP模式下应用Stealth失败: {e}")


    #桌面控制
    def focus_windows(self)->None:
        '''激活并指定当前浏览器窗口'''
        if self.settings.headless:
            return
        import pygetwindow as gw
        time.sleep(0.1)

        candidates:list=[]
        for key_words in ("Chromium","Chrome","Edge","MicrosoftEdge\u202fEdge","Google Chrome"):
            try:
                candidates.extend(gw.getWindowsWithTitle(key_words))
            except Exception:
                continue

        if not candidates:
            raise BrowserError("未找到任何的浏览器窗口")

        #选择面积最大的窗口
        target=max(candidates,key=lambda w:getattr(w,"width",0)*getattr(w,"height",0))
        try:
            if target.isMinimized:
                target.restore()
            target.activate()
            log.debug(f"已激活此窗口：{target.title}")
        except Exception as e:
            msg=str(e)
            if "0" in msg and ("操作成功完成" in msg or "successfully" in msg.lower()):
                log.debug(f"已激活此窗口（win32误报）：{target.title}")
            else:
                raise BrowserError(f"激活窗口失败（可能被windows拒绝）: {e}")



    #访问器
    @property
    def page(self)->Page:
        if self._page is None:
            raise BrowserError("浏览器未启动")
        try:
            closed=self._page.is_closed()
        except Exception:
            closed=True
        
        if closed and self._context is not None:
            pages=[p for p in self._context.pages if not p.is_closed()]
            if pages:
                self._page=pages[-1]
                log.warning(f"检测到原page已关闭，自动切换到context中最新page：{self._page.url}")
            else:
                raise BrowserError("context中没有可用的page")
        return self._page

    def __enter__(self)->"BrowserManager":
            self.start()
            return self
        
    def __exit__(self, exc_typr, exc, tb)->None:
            self.stop()


# 自动善后
#with BrowserManager() as browser:
#    browser.page.goto("https://www.baidu.com")
#    browser.page.click("button")
#    退出with块->自动调用__exit->self.stop()
#    就算中间报错，也会自动关闭浏览器