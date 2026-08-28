"""openai兼容 协议的多模态大模型客户端
qwen-vl-max等模型的调用
"""

from __future__ import annotations
import json
from typing import Any
from openai import OpenAI
from sqlalchemy import exc
from tenacity import retry, retry_if_exception_type, stop_after_attempt,wait_exponential

from webagent.core.config import get_settings
from webagent.core.exceptions import LLMError
from webagent.core.logger import init_logger
from webagent.core.schemas import Action, PageSnapshot, Task
from webagent.perception.collector import PerceptionCollector

log=init_logger()

SYSTEM_PROMPT = """
你是一名世界一流的 Web Agent，负责通过浏览器自动化完成用户的自然语言任务。

你将看到：
1. 用户任务描述
2. 历史动作记录（含每步是否成功、失败原因）
3. 当前页面 URL/标题/可交互元素清单（含稳定 selector）
4. 当前页面截图（图像输入）

你必须输出**单个 JSON 对象**，严格符合如下模式，不允许任何额外文字 / markdown 围栏 / 注释：

{
  "action_type": "click | input | goto | wait | refresh | back | scroll | press_key | done | error",
  "dom_selector": "可选；优先使用元素清单里给出的 selector",
  "screen_x": 可选整数（视口坐标，DOM selector 缺失时给出兜底点击坐标）,
  "screen_y": 可选整数,
  "input_text": "可选；input 动作填写的文本",
  "url": "可选；goto 动作的目标 URL",
  "wait_sec": 可选浮点（wait 动作的秒数）,
  "key": "可选；press_key 的按键",
  "scroll_delta": 可选整数（正数向下，负数向上）,
  "reason": "用一句中文说明本次动作的推理依据，不要超过 60 字"
}

通用规则：
- 当任务已经完成时输出 action_type=done
- 当遇到无法继续时输出 action_type=error
- 优先使用 dom_selector，仅在确实无 selector 可用时给出 screen_x/screen_y
- 不要重复执行历史中已经失败/无效的动作
- 严禁输出 JSON 以外的任何内容

【示例 1】任务：在搜索框中搜索 "OpenAI"
{"action_type":"input","dom_selector":"[data-wa-id=\"12\"]","input_text":"OpenAI","reason":"在搜索框输入关键词"}

【示例 2】任务完成
{"action_type":"done","reason":"已抵达目标页面，任务完成"}
"""
def _build_user_message(
    task: Task,
    snapshot: PageSnapshot,
    history: list[Action],
    last_error : str|None=None,
    prev_url: str|None=None,
    prev_title: str|None=None,
)->list[dict[str]]:
    '''构造一条多模态的用户消息（openai）'''
    history_text="\n".join(
        f"{i+1}. {h.action_type}| selector={h.dom_selector} | text={h.input_text} | reason={h.reason}"
        for i,h in enumerate(history[-10:])
    ) or "空"
    dom_context=PerceptionCollector.render_dom_context(snapshot)

    # 进度提示，让大模型有反思机制，避免重复犯错
    reflexion_parts: list[str]=[]
    if last_error:
        reflexion_parts.append(
            "【上一步失败】\n"
            f"错误：{last_error}\n"
            "请换思路：换selector/滚动/等待/改用screen_x/y坐标兜底"
        )
    else:
        if history:
            reflexion_parts.append(
                "【上一步成功】\n"
                f"动作{history[-1].action_type} 已成功执行，请检查任务是否已经达成"
            )
    # 页面变化提示
    if prev_url is not None and prev_url != snapshot.url:
        reflexion_parts.append(f"【页面已跳转】{prev_url}->{snapshot.url}")
    if prev_title is not None and prev_title != snapshot.title:
        reflexion_parts.append(f"【页面标题变化】{prev_title!r}->{snapshot.title!r}")

    reflexion_parts.append(
       "【完成守则】若任务的目标界面，信息已出现，必须立即输出done"
    )

    reflexion="\n"+"\n".join(reflexion_parts)+"\n"

    # 将以上所有信息组合起来
    text = (
        f"【任务】{task.instruction}\n"
        f"【已执行步骤】\n{history_text}\n"
        f"{reflexion}\n"
        f"【当前页面】\n{dom_context}\n\n"
        f"【文本摘要】{snapshot.text_summary[:300]}\n\n"
        "请基于上方文本和下方截图判断下一步动作，严格按系统提示词输出单个 JSON 对象。"
    )

    return [
        {"type": "text", "text": text},
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{snapshot.screenshot_bs64}"},
        },
    ]  # 关于数据结构： https://llamafactory.readthedocs.io/zh-cn/latest/getting_started/data_preparation.html

def _parse_action(raw:str)->Action:
    '''
    解析大模型输出的动作字符串
    需要兼容三种情况：
    1.纯JSON字符串
    2.包裹在```json代码
    3.前后混杂了自然语言：尝试用首尾大括号截取
    '''
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    if not text.startswith("{"):
        start=text.find("{")
        end=text.find("}")
        if start>=0 and end>start:
            text=text[start:end+1]

    try:
        data=json.loads(text)
    except json.JSONDecodeError as e:   
        raise LLMError(f"模型输出非合法JSON：{raw[:200]!r}") from e

    try:
        return Action.model_validate(data)
    except Exception as e:
        raise LLMError(f"模型输出非合法Action协议：{data}") from e

class VLMClient:
    '''openai语言模型客户端'''
    def __init__(self)->None:
        self.settings=get_settings().llm
        if not self.settings.api_key:
            log.error("请配置环境变量OPENLM_API_KEY环境变量")
        self._client=OpenAI(
            base_url=self.settings.base_url,
            api_key=self.settings.api_key,
            timeout=self.settings.timeout,
            max_retries=0, #由tenacity统一控制
        )

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type(LLMError),
    )
    def decide(
        self,
        task: Task,
        snapshot: PageSnapshot,
        history: list[Action],
        last_error : str|None=None,
        prev_url: str|None=None,
        prev_title: str|None=None,
    )->Action:
        '''根据任务、当前截图、历史动作，返回下一步action'''
        if not self.settings.api_key:
            log.error("请配置环境变量OPENLM_API_KEY环境变量")
    
        messages=[
            {
                "role": "system", 
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user", 
                "content": _build_user_message(task, snapshot, history, last_error, prev_url, prev_title)
            },
        ]

        log.message(f"调用LLM | model={self.settings.model} | elements={len(snapshot.elements)}")
        try:
            resp=self._client.chat.completions.create(
                model=self.settings.model,
                messages=messages,
                temperature=self.settings.temperature,
                response_format={"type": "json_object"},
            )
        except TypeError:
            #部分供应商不支持response_format，回落
            resp=self._client.chat.completions.create(
                model=self.settings.model,
                messages=messages,
                temperature=self.settings.temperature,
            )
        except Exception as e:
            raise LLMError(f"调用LLM失败：{e}") from e
        
        if not resp.choices:
            raise LLMError("LLM模型输出空choices")
        content=resp.choices[0].message.content or ""
        log.debug(f"LLM模型输出：{content[:300]}")

        action=_parse_action(content)
        log.info(f"AI决策->{action.action_type} | selector={action.selector} | reason={action.reason}")
        return action


