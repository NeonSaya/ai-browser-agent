"""项目级异常体系。"""
class WebAgentError(Exception):
    """所有自定义异常的基类。"""


class ConfigError(WebAgentError):
    """配置缺失或非法。"""


class BrowserError(WebAgentError):
    """浏览器执行层异常。"""


class PerceptionError(WebAgentError):
    """感知采集异常。"""


class LLMError(WebAgentError):
    """大模型调用 / 输出解析异常。"""


class ActionExecutionError(WebAgentError):
    """动作执行失败（DOM + 坐标兜底均失败）。"""


class AgentLoopError(WebAgentError):
    """Agent 状态机循环异常（超步数、死循环等）。"""