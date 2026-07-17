"""多轮上下文记忆 — 单会话隔离，支持接续提问"""
import json
import os
import time
from typing import Optional

from .settings import settings


class ConversationContext:
    """单次对话上下文"""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.history: list[dict] = []  # [{"role":"user","content":...}, {"role":"assistant","content":...}]
        self.last_intent: Optional[str] = None
        self.last_module_result: Optional[dict] = None
        self.last_log_file: Optional[str] = None
        self.last_log_lines: list[str] = []
        self.last_device_type: Optional[str] = None
        self.last_scenario_id: Optional[str] = None
        self.created_at = time.time()
        self.updated_at = time.time()

    def add_turn(self, role: str, content: str):
        """添加一轮对话"""
        self.history.append({"role": role, "content": content, "timestamp": time.time()})
        self.updated_at = time.time()
        # 限制历史轮数
        max_turns = settings.max_context_turns * 2
        if len(self.history) > max_turns:
            self.history = self.history[-max_turns:]

    def get_recent_history(self, n: int = 3) -> list[dict]:
        """获取最近 n 轮对话"""
        pairs = []
        for msg in self.history[-n * 2:]:
            pairs.append({"role": msg["role"], "content": msg["content"]})
        return pairs

    def clear(self):
        """清空上下文"""
        self.history.clear()
        self.last_intent = None
        self.last_module_result = None
        self.last_log_file = None
        self.last_log_lines = []
        self.last_device_type = None
        self.last_scenario_id = None

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "history": self.history[-10:],  # 只保存最近 10 轮
            "last_intent": self.last_intent,
            "last_log_file": self.last_log_file,
            "last_device_type": self.last_device_type,
        }


class ContextManager:
    """全局上下文管理器 — 管理多个会话"""

    def __init__(self):
        self._sessions: dict[str, ConversationContext] = {}
        self._current_session_id: Optional[str] = None

    @property
    def current(self) -> Optional[ConversationContext]:
        if self._current_session_id and self._current_session_id in self._sessions:
            return self._sessions[self._current_session_id]
        return None

    def new_session(self, session_id: str = None) -> ConversationContext:
        """创建新会话"""
        sid = session_id or f"session_{int(time.time())}"
        ctx = ConversationContext(sid)
        self._sessions[sid] = ctx
        self._current_session_id = sid
        return ctx

    def get_or_create(self, session_id: str = None) -> ConversationContext:
        """获取或创建会话"""
        sid = session_id or self._current_session_id
        if sid and sid in self._sessions:
            self._current_session_id = sid
            return self._sessions[sid]
        return self.new_session(sid)

    def clear_current(self):
        """清空当前会话"""
        if self.current:
            self.current.clear()

    def save_chat_log(self):
        """保存对话日志到文件"""
        ctx = self.current
        if not ctx or not ctx.history:
            return
        try:
            log_dir = settings.chat_log_dir_path
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            path = os.path.join(log_dir, f"chat_{timestamp}.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(ctx.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception:
            pass


_context_manager = None


def get_context_manager() -> ContextManager:
    global _context_manager
    if _context_manager is None:
        _context_manager = ContextManager()
    return _context_manager