"""LLM 客户端 — 同步版，直接 requests 调用 OpenAI 兼容 API"""
import json
import time
import requests
from typing import Optional

from .settings import settings


class LLMClient:
    """大模型客户端（同步，requests 实现，不依赖 openai SDK）"""

    def __init__(self):
        self.api_key = settings.llm_api_key
        self.base_url = settings.llm_base_url.rstrip("/")
        self.model = settings.llm_model_name
        self.temperature = settings.llm_temperature
        self.timeout = settings.llm_timeout
        self.max_tokens = settings.llm_max_tokens

    def chat(self, messages: list[dict], temperature: Optional[float] = None,
             max_tokens: Optional[int] = None) -> dict:
        """调用 LLM，返回 {content, success, error}"""
        if not self.api_key:
            return {"content": None, "success": False,
                    "error": "LLM API Key 未配置。请设置 LLM_API_KEY 环境变量或运行首次配置。"}

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": max_tokens if max_tokens is not None else self.max_tokens,
        }

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return {"content": content, "success": True, "error": None}
        except requests.exceptions.Timeout:
            return {"content": None, "success": False, "error": f"LLM 请求超时（{self.timeout}s）"}
        except requests.exceptions.ConnectionError:
            return {"content": None, "success": False, "error": f"无法连接到 {self.base_url}，请检查网络"}
        except requests.exceptions.HTTPError as e:
            return {"content": None, "success": False, "error": f"LLM HTTP 错误: {e}"}
        except Exception as e:
            return {"content": None, "success": False, "error": f"LLM 调用异常: {e}"}

    def chat_json(self, messages: list[dict], temperature: Optional[float] = None,
                  max_tokens: Optional[int] = None) -> dict:
        """调用 LLM 并解析返回 JSON"""
        result = self.chat(messages, temperature, max_tokens)
        if not result["success"] or not result["content"]:
            return {"success": False, "error": result["error"], "data": None}

        content = result["content"].strip()
        # 尝试提取 JSON（LLM 可能用 ```json 包裹）
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        try:
            data = json.loads(content)
            return {"success": True, "error": None, "data": data}
        except json.JSONDecodeError:
            return {"success": False, "error": "LLM 返回内容不是有效 JSON", "data": content}


class EmbeddingClient:
    """Embedding 客户端 — 调用 API 生成文本向量"""

    def __init__(self):
        self.api_key = settings.llm_api_key
        self.base_url = settings.llm_base_url.rstrip("/")
        self.model = settings.embedding_model
        self.timeout = 30

    def embed(self, text: str) -> Optional[list[float]]:
        """将文本转为向量"""
        if not self.api_key:
            return None

        url = f"{self.base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "input": text,
        }

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            embedding = data.get("data", [{}])[0].get("embedding")
            return embedding
        except Exception:
            return None

    def embed_batch(self, texts: list[str]) -> list[Optional[list[float]]]:
        """批量文本向量化"""
        results = []
        for text in texts:
            results.append(self.embed(text))
        return results


_llm_instance = None
_embed_instance = None


def get_llm() -> LLMClient:
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = LLMClient()
    return _llm_instance


def get_embedding() -> EmbeddingClient:
    global _embed_instance
    if _embed_instance is None:
        _embed_instance = EmbeddingClient()
    return _embed_instance
