"""意图分类器 — 调用 LLM 对用户输入做 6 类意图识别"""
import json
from typing import Optional

from .llm_client import get_llm
from .prompts import build_intent_messages
from .settings import settings


INTENT_MODULES = {
    "log_parse": "log_parse",
    "collection": "log_collect",
    "compliance": "compliance",
    "script_gen": "script_gen",
    "training": "training",
    "correlation": "log_correlate",
    "general": None,  # 通用问答，无需调业务模块
}


class IntentResult:
    """意图分类结果"""
    def __init__(self, intent: str = "general", confidence: float = 0.0,
                 params: dict = None, reason: str = ""):
        self.intent = intent
        self.confidence = confidence
        self.params = params or {}
        self.reason = reason
        self.module = INTENT_MODULES.get(intent)

    @property
    def is_actionable(self) -> bool:
        """是否是可调业务模块的意图（非通用问答）"""
        return self.intent != "general" and self.confidence >= settings.intent_confidence_threshold

    @property
    def is_general(self) -> bool:
        return self.intent == "general" or self.confidence < settings.intent_confidence_threshold

    def __repr__(self):
        return f"Intent({self.intent}, conf={self.confidence:.2f}, module={self.module})"


class IntentClassifier:
    """LLM 意图分类器"""

    def classify(self, user_input: str) -> IntentResult:
        """对用户输入做意图分类"""
        if not user_input or not user_input.strip():
            return IntentResult("general", 0.0, {}, "空输入")

        messages = build_intent_messages(user_input.strip())
        llm = get_llm()
        result = llm.chat_json(messages, temperature=0.05, max_tokens=500)

        if not result["success"] or not result.get("data"):
            # LLM 失败时降级为通用问答
            return IntentResult("general", 0.0, {}, f"LLM 分类失败: {result.get('error', 'unknown')}")

        data = result["data"]
        intent = data.get("intent", "general")
        confidence = float(data.get("confidence", 0.0))
        params = data.get("params", {})
        reason = data.get("reason", "")

        # 验证 intent 合法性
        if intent not in INTENT_MODULES:
            intent = "general"
            confidence = 0.0

        return IntentResult(intent, confidence, params, reason)


_intent_classifier = None


def get_classifier() -> IntentClassifier:
    global _intent_classifier
    if _intent_classifier is None:
        _intent_classifier = IntentClassifier()
    return _intent_classifier