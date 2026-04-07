"""记忆工具 - 存储和检索对话历史"""

import json
import os
from datetime import datetime
from typing import Optional, Any
from pathlib import Path

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field


class MemoryInput(BaseModel):
    """记忆工具输入参数"""
    action: str = Field(description="执行的操作: 'save', 'get', 或 'clear'")
    key: Optional[str] = Field(default=None, description="用于检索的记忆键")
    content: Optional[str] = Field(default=None, description="要保存的内容")


class MemoryStore:
    """简单的基于文件的记忆存储"""
    
    def __init__(self, storage_dir: Optional[str] = None):
        if storage_dir is None:
            storage_dir = os.path.join(os.path.expanduser("~"), ".aid", "memory")
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.memory_file = self.storage_dir / "conversations.json"
        self._memories: dict[str, Any] = {}
        self._load_memories()
    
    def _load_memories(self):
        """从文件加载记忆"""
        if self.memory_file.exists():
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    self._memories = json.load(f)
            except Exception:
                self._memories = {}
        else:
            self._memories = {}
    
    def _save_memories(self):
        """保存记忆到文件"""
        try:
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(self._memories, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存记忆时出错: {e}")
    
    def save(self, key: str, content: str, metadata: Optional[dict] = None):
        """保存一条记忆"""
        self._memories[key] = {
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        self._save_memories()
    
    def get(self, key: str) -> Optional[dict[str, Any]]:
        """通过键获取记忆"""
        return self._memories.get(key)
    
    def get_all(self) -> dict[str, Any]:
        """获取所有记忆"""
        return self._memories.copy()
    
    def search(self, query: str) -> list[dict[str, Any]]:
        """按内容搜索记忆"""
        results = []
        query_lower = query.lower()
        for key, value in self._memories.items():
            content = value.get("content", "")
            if query_lower in content.lower():
                results.append({"key": key, **value})
        return results
    
    def clear(self):
        """清除所有记忆"""
        self._memories = {}
        self._save_memories()


class MemoryTool(BaseTool):
    """管理对话记忆的工具"""
    
    name: str = "memory_manager"
    description: str = """管理对话记忆和检索过往信息。
    
    使用此工具来:
    - 保存对话中的重要信息
    - 检索之前讨论过的话题
    - 搜索相关的过往对话
    
    操作:
    - 'save': 使用键保存内容
    - 'get': 通过键检索内容
    - 'search': 按关键词搜索记忆
    - 'clear': 清除所有记忆
    """
    args_schema: type[BaseModel] = MemoryInput
    
    def __init__(self):
        super().__init__()
        self._store = MemoryStore()
    
    def _run(self, action: str, key: Optional[str] = None, content: Optional[str] = None) -> str:
        """执行记忆操作"""
        action = action.lower()
        
        if action == "save":
            if not key or not content:
                return "错误: 'save'操作需要'key'和'content'参数。"
            self._store.save(key, content)
            return f"记忆已保存，键: {key}"
        
        elif action == "get":
            if not key:
                return "错误: 'get'操作需要'key'参数。"
            memory = self._store.get(key)
            if memory:
                return f"记忆 [{key}]: {memory['content']}"
            return f"未找到键为'{key}'的记忆"
        
        elif action == "search":
            if not content:
                return "错误: 'search'操作需要'content'(搜索查询)参数。"
            results = self._store.search(content)
            if results:
                formatted = []
                for r in results[:5]:  # 限制5个结果
                    formatted.append(f"- {r['key']}: {r['content'][:100]}...")
                return "搜索结果:\n" + "\n".join(formatted)
            return "未找到匹配的记忆。"
        
        elif action == "clear":
            self._store.clear()
            return "所有记忆已清除。"
        
        else:
            return f"错误: 未知操作'{action}'。请使用'save', 'get', 'search', 或'clear'。"
    
    async def _arun(self, action: str, key: Optional[str] = None, content: Optional[str] = None) -> str:
        """异步执行"""
        return self._run(action, key, content)


class ConversationMemory:
    """管理对话上下文的辅助类"""

    def __init__(self):
        self.store = MemoryStore()
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

