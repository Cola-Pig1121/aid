from typing import AsyncIterator, List, Optional, Any
from openai import AsyncOpenAI
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.callbacks import CallbackManagerForLLMRun
from pydantic import Field

from src.config import get_config


class LLMClient:
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ):
        config = get_config()
        self.provider = provider or self._detect_provider(config)

        if self.provider == "modelscope":
            self.api_key = api_key or config.modelscope_api_key
            self.base_url = base_url or config.modelscope_base_url
            self.model = model or config.modelscope_model
        else:
            self.api_key = api_key or config.openrouter_api_key
            self.base_url = base_url or config.openrouter_base_url
            self.model = model or config.openrouter_model

        if not self.api_key:
            raise ValueError(f"API key is required for {self.provider}")

        self.temperature = temperature
        self.max_tokens = max_tokens

        self.client = AsyncOpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
        )

    def _detect_provider(self, config) -> str:
        if config.modelscope_api_key:
            return "modelscope"
        return "openrouter"
    
    async def chat(
        self,
        messages: list[dict[str, str]],
        stream: bool = False,
    ) -> AsyncIterator[str]:
        
        if stream:
            async for chunk in self._stream_chat(messages):
                yield chunk
        else:
            yield await self.complete(messages)

    async def complete(self, messages: list[dict[str, Any]]) -> str:
        """Return a single non-streaming model response."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        return self._extract_response_text(response)

    def _extract_response_text(self, response: Any) -> str:
        """从兼容 OpenAI 的响应中提取可展示文本。"""
        choices = getattr(response, "choices", None) or []
        if not choices:
            return "模型未返回可用结果。"

        message = getattr(choices[0], "message", None)
        if message is None:
            return "模型返回了空消息。"

        content = getattr(message, "content", None)
        if isinstance(content, str):
            return content

        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str):
                        parts.append(text)
                else:
                    text = getattr(item, "text", None)
                    if isinstance(text, str):
                        parts.append(text)
            if parts:
                return "".join(parts)

        refusal = getattr(message, "refusal", None)
        if isinstance(refusal, str) and refusal.strip():
            return refusal

        reasoning = getattr(message, "reasoning", None)
        if isinstance(reasoning, str) and reasoning.strip():
            return reasoning

        return "模型返回成功，但没有可解析的文本内容。"
    
    async def _stream_chat(
        self,
        messages: list[dict[str, str]],
    ) -> AsyncIterator[str]:
        
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            stream=True,
        )
        
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class LLMLangChain(BaseChatModel):
    
    client: LLMClient = Field(default=None)
    api_key: Optional[str] = Field(default=None)
    base_url: Optional[str] = Field(default=None)
    model: Optional[str] = Field(default=None)
    provider: Optional[str] = Field(default=None)
    temperature: float = Field(default=0.7)
    max_tokens: int = Field(default=2048)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.client = LLMClient(
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model,
            provider=self.provider,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
    
    @property
    def _llm_type(self) -> str:
        return self.client.provider
    
    def _convert_messages(self, messages: List[BaseMessage]) -> list[dict[str, str]]:
        converted = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                converted.append({"role": "system", "content": msg.content})
            elif isinstance(msg, HumanMessage):
                converted.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                converted.append({"role": "assistant", "content": msg.content})
        return converted
    
    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        import asyncio
        
        converted_messages = self._convert_messages(messages)
        
        loop = asyncio.get_event_loop()
        response_text = loop.run_until_complete(
            self._async_generate(converted_messages)
        )
        
        message = AIMessage(content=response_text)
        generation = ChatGeneration(message=message)
        return ChatResult(generations=[generation])
    
    async def _async_generate(self, messages: list[dict[str, str]]) -> str:
        return await self.client.complete(messages)
    
    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        converted_messages = self._convert_messages(messages)
        response_text = await self._async_generate(converted_messages)
        
        message = AIMessage(content=response_text)
        generation = ChatGeneration(message=message)
        return ChatResult(generations=[generation])

OpenRouterClient = LLMClient
