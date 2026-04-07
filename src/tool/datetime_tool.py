"""日期时间工具"""

from datetime import datetime
from langchain_core.tools import BaseTool
from pydantic import BaseModel


class DateTimeInput(BaseModel):
    """日期时间工具输入"""
    pass


class DateTimeTool(BaseTool):
    """获取当前日期和时间的工具"""
    
    name: str = "get_current_datetime"
    description: str = "获取当前日期和时间。在需要知道当前时间时使用。"
    args_schema: type[BaseModel] = DateTimeInput
    
    def _run(self) -> str:
        """获取当前日期时间"""
        now = datetime.now()
        return f"当前日期和时间: {now.strftime('%Y-%m-%d %H:%M:%S')}"
    
    async def _arun(self) -> str:
        """异步获取当前日期时间"""
        return self._run()
