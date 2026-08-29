from __future__ import annotations

import base64
import io
from tracemalloc import Snapshot
from typing import TYPE_CHECKING

from PIL import Image
from sqlalchemy import exc

from webagent.core.config import get_settings
from webagent.core.exceptions import PerceptionError
from webagent.core.logger import init_logger
from webagent.core.schemas import DomElement,PageSnapshot

if TYPE_CHECKING:
    from playwright.sync_api import Page

log=init_logger()

# 在浏览器内执行的JS，抓取可交互的元素，按规则打标之后返回json数据
# 同时为每个采集到的元素临时写入'data-wa-id'属性，便于playwright 100%命中
_COLLECT_JS = r"""
(maxElements) => {
  const SELECTOR = [
    'a[href]', 'button',
    'input:not([type=hidden])', 'textarea', 'select',
    '[role=button]', '[role=link]', '[role=textbox]', '[role=combobox]',
    '[role=menuitem]', '[role=tab]', '[role=checkbox]', '[role=radio]',
    '[contenteditable=""]', '[contenteditable=true]',
    '[onclick]', 'label[for]'
  ].join(',');

  // 清理上一次注入的 data-wa-id，避免污染
  document.querySelectorAll('[data-wa-id]').forEach(el => el.removeAttribute('data-wa-id'));

  const vw = window.innerWidth;
  const vh = window.innerHeight;

  const all = Array.from(document.querySelectorAll(SELECTOR));
  const result = [];

  const isVisible = (el) => {
    const style = window.getComputedStyle(el);
    if (style.visibility === 'hidden' || style.display === 'none' || style.opacity === '0') return false;
    const rect = el.getBoundingClientRect();
    if (rect.width <= 1 || rect.height <= 1) return false;
    return true;
  };

  const clip = (s, n) => (s || '').replace(/\s+/g, ' ').trim().slice(0, n);

  let idx = 0;
  for (const el of all) {
    if (!isVisible(el)) continue;
    const rect = el.getBoundingClientRect();
    const inViewport = rect.bottom > 0 && rect.right > 0 && rect.top < vh && rect.left < vw;

    const tag = el.tagName.toLowerCase();
    let text = clip(el.innerText || el.value || '', 80);
    if (!text) text = clip(el.getAttribute('aria-label') || el.getAttribute('placeholder') || el.getAttribute('title') || el.getAttribute('alt') || '', 80);

    // 标记 data-wa-id，作为稳定 selector 的兜底
    el.setAttribute('data-wa-id', String(idx));
    let selector = `[data-wa-id="${idx}"]`;

    result.push({
      index: idx,
      tag,
      text,
      role: el.getAttribute('role') || null,
      name: el.getAttribute('name') || el.getAttribute('aria-label') || null,
      selector,
      area: Math.round(rect.width * rect.height),
      inViewport,
      bbox: [Math.round(rect.left), Math.round(rect.top), Math.round(rect.width), Math.round(rect.height)],
    });
    idx += 1;
  }

  // 排序：视口内优先 → 面积大优先 → DOM 顺序
  result.sort((a, b) => {
    if (a.inViewport !== b.inViewport) return a.inViewport ? -1 : 1;
    if (a.area !== b.area) return b.area - a.area;
    return a.index - b.index;
  });

  return {
    url: location.href,
    title: document.title,
    text_summary: clip(document.body ? document.body.innerText : '', 600),
    viewport: [vw, vh],
    elements: result.slice(0, maxElements),
  };
}
"""

class PerceptionCollector:
    '''页面感知采集器（双模态）'''
    def __init__(self)->None:
        self.cfg= get_settings().agent
        
    #主入口
    def capture(self,page:"Page")->PageSnapshot:
        '''采集页面感知'''
        try:
            data=page.evaluate(_COLLECT_JS, self.cfg.dom_max_elements)
        except Exception as e:
            raise PerceptionError(f"DOM采集失败：{e}")
        elements=[
            DomElement(
                index=item['index'],
                tag=item['tag'],
                text=item.get("text") or "",
                selector=item['selector'],
                role=item.get("role"),
                name=item.get("name"),
                bbox=tuple(item["bbox"])if item.get("bbox") else None,
                in_viewport=bool(item.get("inViewport",False)),
            )
            for item in data['elements']
        ]
        screenshot_b64=self._screenshot_b64(page)

        snapshot=PageSnapshot(
            url=data.get("url",""),
            title=data.get("title",""),
            text_summary=data.get("text_summary",""),
            elements=elements,
            screenshot_bs64=screenshot_b64,
            viewport=tuple(data.get("viewport") or [0,0]),
        )
        log.debug(f"感知完成 | url={snapshot.url} | elements={len(elements)} | screenshot={len(screenshot_b64)//1024}KB ")
        return snapshot

    # 截图处理
    def _screenshot_b64(self,page:"Page")->str:
        '''采集页面截图，等比缩放，base64'''
        try:
            raw=page.screenshot(type="png",full_page=False)
        except Exception as e:
            raise PerceptionError(f"截图采集失败：{e}")

        try:
            img=Image.open(io.BytesIO(raw))
            max_edge=self.cfg.screenshot_max_edge
            if max(img.size)>max_edge:
                ratio=max_edge/max(img.size)
                new_size=(int(img.size[0]*ratio),int(img.size[1]*ratio))
                img=img.resize(new_size,Image.LANCZOS)
            buf=io.BytesIO()
            img.save(buf,format="PNG",optimize=True)
            raw=buf.getvalue()
        except Exception as e:
            raise PerceptionError(f"截图压缩失败，回落到原图：{e}")

        return base64.b64encode(raw).decode("ascii")

    #文本上下文
    @staticmethod
    def render_dom_context(snapshot:PageSnapshot,limit:int | None=None)->str:
        '''渲染DOM上下文，喂给llm'''
        lines=[f"URL:{snapshot.url}",f"TITLE:{snapshot.title}","ELEMENTS:"]
        items=snapshot.elements if limit is None else snapshot.elements[:limit]
        for el in items:
            text=el.text or el.name or ""
            text=text[:60]
            lines.append(
                f"[{el.index}] <{el.tag}> name={el.name!r} selector={el.selector} text={text!r}"
            )
        return "\n".join(lines)
            