"""大模型工厂 — 统一创建 LLM 客户端实例"""

from abc import ABC, abstractmethod
from typing import Optional

from openai import AsyncOpenAI

from common.logger import LogManager

logger = LogManager.get_logger()


class BaseLLMClient(ABC):
    """LLM 客户端基类"""

    def __init__(self, api_key: str, base_url: str, model_name: str, temperature: float = 0.1, timeout: int = 10):
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model_name
        self.temperature = temperature
        self.timeout = timeout
        self.client: Optional[AsyncOpenAI] = None

    @abstractmethod
    async def chat(self, messages: list[dict], temperature: Optional[float] = None, timeout: Optional[int] = None) -> dict:
        """调用大模型，返回 {content, success, error}"""
        ...

    async def close(self):
        """关闭客户端会话"""
        if self.client:
            await self.client.close()


class DeepSeekClient(BaseLLMClient):
    """DeepSeek API 实现"""

    async def chat(self, messages: list[dict], temperature: Optional[float] = None, timeout: Optional[int] = None) -> dict:
        temp = temperature or self.temperature
        t = timeout or self.timeout
        try:
            self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url, timeout=t)
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temp,
            )
            content = response.choices[0].message.content or ""
            return {"content": content, "success": True, "error": None}
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            return {"content": None, "success": False, "error": str(e)}


class LightweightClient(BaseLLMClient):
    """轻量模型实现（Qwen/Distill）"""

    async def chat(self, messages: list[dict], temperature: Optional[float] = None, timeout: Optional[int] = None) -> dict:
        temp = temperature or self.temperature
        t = timeout or self.timeout
        try:
            self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url, timeout=t)
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temp,
                max_tokens=512,
            )
            content = response.choices[0].message.content or ""
            return {"content": content, "success": True, "error": None}
        except Exception as e:
            logger.error(f"轻量 LLM 调用失败: {e}")
            return {"content": None, "success": False, "error": str(e)}


class LLMFactory:
    """大模型工厂 — 统一创建和管理 LLM 客户端"""

    _main_llm: Optional[BaseLLMClient] = None
    _light_llm: Optional[BaseLLMClient] = None

    @classmethod
    def create(cls, model_type: str = "main") -> BaseLLMClient:
        """根据配置返回对应 LLM 实例"""
        from app.settings import settings

        if model_type == "main":
            return DeepSeekClient(
                api_key=settings.llm_api_key,
                base_url=settings.llm_base_url,
                model_name=settings.llm_model_name,
                temperature=settings.llm_temperature,
                timeout=settings.llm_timeout,
            )
        elif model_type == "light":
            return LightweightClient(
                api_key=settings.llm_api_key,
                base_url=settings.llm_base_url,
                model_name=settings.llm_light_model_name,
                temperature=settings.llm_temperature,
                timeout=settings.llm_timeout,
            )
        raise ValueError(f"未知模型类型: {model_type}")

    @classmethod
    async def get_main_llm(cls) -> BaseLLMClient:
        """获取主力模型（单例）"""
        if cls._main_llm is None:
            cls._main_llm = cls.create("main")
        return cls._main_llm

    @classmethod
    async def get_light_llm(cls) -> BaseLLMClient:
        """获取轻量模型（单例）"""
        if cls._light_llm is None:
            cls._light_llm = cls.create("light")
        return cls._light_llm

    @classmethod
    async def close_all(cls):
        """关闭所有 LLM 客户端"""
        if cls._main_llm:
            await cls._main_llm.close()
        if cls._light_llm:
            await cls._light_llm.close()