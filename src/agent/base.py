"""基础Agent类"""

from abc import ABC, abstractmethod
from typing import Any, List, Optional
from pydantic import BaseModel, Field


class AgentAction(BaseModel):
    tool: str = Field(description="要调用的工具名称")
    tool_input: str = Field(description="工具输入")
    log: str = Field(default="", description="Agent思考日志")


class AgentFinish(BaseModel):
    return_values: dict[str, Any] = Field(default_factory=dict)
    log: str = Field(default="", description="Agent思考日志")


class AgentState(BaseModel):
    messages: list[dict[str, str]] = Field(default_factory=list)
    agent_scratchpad: List[AgentAction] = Field(default_factory=list)
    tool_responses: list[dict[str, str]] = Field(default_factory=list)
    
    class Config:
        arbitrary_types_allowed = True


class BaseAgent(ABC):
    """基础Agent类"""
    
    def __init__(self, llm: Any, tools: List[Any], system_prompt: Optional[str] = None):
        self.llm = llm
        self.tools = tools
        self.tools_dict = {tool.name: tool for tool in tools}
        self.system_prompt = system_prompt or ""
    
    @abstractmethod
    async def run(self, query: str) -> str:
        """使用查询运行Agent"""
        pass
    
    async def _call_tool(self, tool_name: str, tool_input: str) -> str:
        """通过名称调用工具"""
        tool = self.tools_dict.get(tool_name)
        if not tool:
            return f"错误: 工具 '{tool_name}' 未找到。可用工具: {list(self.tools_dict.keys())}"
        
        try:
            result = await tool.ainvoke(tool_input)
            return str(result)
        except Exception as e:
            return f"调用工具 '{tool_name}' 时出错: {str(e)}"
