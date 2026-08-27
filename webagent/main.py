import sys
import base64
from datetime import datetime
from pathlib import Path
from webagent.core.config import PROJECT_ROOT, get_settings
from webagent.core.logger import init_logger
from webagent.core.storage import init_db

SCREENSHOT_DIR=Path(__file__).parent.parent/"screenshots"
SCREENSHOT_DIR.mkdir(exist_ok=True)

def cmd_self_check()->int:
    """
    验证核心层所有组件能正常工作
    """
    log=init_logger()
    settings=get_settings()
    log.info("webagent启动")
    log.info(f"项目根目录：{PROJECT_ROOT}")
    log.info(f"Python版本：{sys.version}")
    log.info(f'LLM->BaseURL={settings.llm.base_url}|Model={settings.llm.model}|api_key={"***" if settings.llm.api_key else "未配置"}')
    log.info(f"Broswer->mode={settings.browser.mode} | headless ={settings.browser.headless}")
    log.info(f"agent->max_steps={settings.agent.max_steps}")
    init_db()
    log.info("自检通过")
    return 0

def cmd_browser_smoke()->int:
    """
    验证浏览器是否能正常启动，验证playwright+stealth+窗口控制链路是否正常
    """
    log=init_logger()
    log.info("webagent浏览器冒烟测试")
    init_db()
    from webagent.executor.browser import BrowserManager

    target_url="https://example.com"
    out_path=SCREENSHOT_DIR/f"smoke_{datetime.now():%Y%m%d_%H%M%S}.png"

    log.info(f"浏览器冒烟开始：{target_url}")
    with BrowserManager() as bm:
        page=bm.page
        page.goto(target_url,wait_until="load",timeout=30_000)
        log.info(f"页面标题：{page.title()}")
        page.screenshot(path=str(out_path),full_page=True)
        log.success(f"截图已保存：{out_path}")

        #验证stealth:检查navigator.webdriver是否被抹掉
        webdriver_flag=page.evaluate("(()=>navigator.webdriver)")
        log.info(f"navigator.webdriver: {webdriver_flag}")
    
    log.success("浏览器冒烟测试通过")
    return 0

def cmd_perceive_smoke()->int:
    """
    验证感知层：DOM摘要采集+截图bs64+DOM上下文渲染
    """
    log=init_logger()
    log.info("webagent感知冒烟测试")
    init_db()

    from webagent.executor.browser import BrowserManager
    from webagent.perception.collector import PerceptionCollector

    target_url="https://www.bing.com"
    log.info(f"感知冒烟开始：{target_url}")
    ok=True
    with BrowserManager() as bm:
        page=bm.page
        page.goto(target_url,wait_until="load",timeout=30_000)
        snapshot=PerceptionCollector().capture(page)

        # 1.DOM摘要：元素数量/视口内数量/首个元素详情
        if snapshot.elements:
            in_vp=sum(1 for el in snapshot.elements if el.in_viewport)
            log.success(f"DOM摘要获取成功，元素数量：{len(snapshot.elements)}（视口内 {in_vp}）")
            log.info(f"URL：{snapshot.url}")
            log.info(f"标题：{snapshot.title}")
            log.info(f"文本摘要：{snapshot.text_summary[:80]!r}")
            el=snapshot.elements[0]
            log.info(f"首个元素：<{el.tag}> selector={el.selector} bbox={el.bbox} text={el.text[:20]!r}")
        else:
            log.error("DOM摘要获取失败：未采集到任何元素")
            ok=False

        # 2.截图bs64：非空+大小+解码落盘人工核对
        if snapshot.screenshot_bs64:
            size_kb=len(snapshot.screenshot_bs64)/1024
            log.success(f"截图bs64获取成功，大小：{size_kb:.2f} KB")
            out_path=SCREENSHOT_DIR/f"perceive_{datetime.now():%Y%m%d_%H%M%S}.png"
            out_path.write_bytes(base64.b64decode(snapshot.screenshot_bs64))
            log.info(f"截图已保存：{out_path}")
        else:
            log.error("截图bs64获取失败")
            ok=False

        # 3.视口尺寸
        log.info(f"视口尺寸：{snapshot.viewport[0]}x{snapshot.viewport[1]}")

        # 4.DOM上下文渲染（最终喂给LLM的产物）
        context=PerceptionCollector.render_dom_context(snapshot,limit=10)
        log.info(f"DOM上下文预览（前10个元素）：\n{context}")

    if ok:
        log.success("感知冒烟测试通过")
    return 0 if ok else 1
