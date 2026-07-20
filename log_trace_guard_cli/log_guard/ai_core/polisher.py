from __future__ import annotations
"""结果润色器 — 将机器结构化结果转为通俗解读"""
from typing import Optional

from .llm_client import get_llm
from .prompts import get_system_prompt, build_chat_messages
from .rag_engine import get_rag


class ResponsePolisher:
    """结果润色器
    - 将业务模块返回的机器结果用 LLM 做通俗解读
    - 高危风险重点标注
    - 适配新手理解
    """

    def polish(self, module: str, user_input: str,
               original_result: dict, rag_context: str = "",
               history: list[dict] = None) -> str:
        """润色业务模块结果"""
        if not original_result:
            return "暂无返回结果。"

        import json
        result_str = json.dumps(original_result, ensure_ascii=False, indent=2)

        messages = build_chat_messages(
            module=module,
            user_input=user_input,
            rag_context=rag_context,
            history=history,
            original_result=result_str,
        )

        llm = get_llm()
        resp = llm.chat(messages)
        if resp["success"] and resp["content"]:
            return resp["content"].strip()

        # LLM 失败，返回原始结果
        return f"（智能解读不可用，展示原始结果）\n{result_str}"

    def direct_answer(self, user_input: str,
                      rag_context: str = "",
                      history: list[dict] = None) -> str:
        """通用问答：不调业务模块，直接 LLM + RAG 回答"""
        messages = build_chat_messages(
            module="general",
            user_input=user_input,
            rag_context=rag_context,
            history=history,
        )

        llm = get_llm()
        resp = llm.chat(messages)
        if resp["success"] and resp["content"]:
            return resp["content"].strip()

        # LLM 失败：用 RAG 结果兜底
        if rag_context:
            return f"基于知识库检索结果：\n{rag_context[:1500]}"
        return f"抱歉，LLM 暂时不可用（{resp.get('error', '未知错误')}），请稍后再试。"


_polisher = None


def get_polisher() -> ResponsePolisher:
    global _polisher
    if _polisher is None:
        _polisher = ResponsePolisher()
    return _polisher