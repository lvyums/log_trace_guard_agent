"""全局 Prompt 模板管理"""

from typing import Optional

# 全局 System Prompt
GLOBAL_SYSTEM_PROMPT = """你是一个专业的日志安全分析助手，请严格遵循以下规则：
1. 基于知识库内容回答，不要编造信息
2. 输出结构化、分点、可直接落地的内容
3. 保持客观，不确定的内容标注"暂无依据"
4. 涉及安全风险时明确标注危害等级"""

# 模块级 System Prompt
MODULE_PROMPTS = {
    "default": "请基于提供的信息给出准确、专业的回答。",
    "log_parse": "你是一个日志解析专家。请识别日志类型，提取关键字段，并给出行为研判。",
}


class PromptManager:
    """全局 Prompt 模板管理"""

    _version = "1.0.0"

    @classmethod
    def get_system_prompt(cls, module: str = "default") -> str:
        """获取模块 System Prompt，注入全局约束"""
        module_prompt = MODULE_PROMPTS.get(module, MODULE_PROMPTS["default"])
        return f"{GLOBAL_SYSTEM_PROMPT}\n\n{module_prompt}"

    @classmethod
    def build_messages(cls, module: str, user_input: str, context: Optional[dict] = None) -> list[dict]:
        """组装完整消息列表（system + 用户输入 + 上下文）"""
        messages = [
            {"role": "system", "content": cls.get_system_prompt(module)},
        ]
        if context and "rag_context" in context:
            messages.append({
                "role": "system",
                "content": f"知识库参考信息：\n{context['rag_context']}",
            })
        messages.append({"role": "user", "content": user_input})
        return messages

    @classmethod
    def get_version(cls) -> str:
        """返回当前 Prompt 模板版本号"""
        return cls._version