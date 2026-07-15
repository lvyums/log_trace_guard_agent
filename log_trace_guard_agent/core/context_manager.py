"""模块间上下文传递管理 — 按请求ID隔离，支持TTL过期清理"""

from datetime import datetime, timedelta
from typing import Optional
from threading import Lock

from app.schemas.context_schema import ModuleContextSchema, ModuleStatus

# 向后兼容别名
ModuleContext = ModuleContextSchema


class ContextManager:
    """模块间上下文传递 — 管理请求全链路的模块状态和数据
    支持 TTL 过期自动清理，按请求唯一 ID 隔离，避免内存堆积、数据串扰
    """

    _instances: dict[str, "ContextManager"] = {}
    _lock = Lock()
    _default_ttl: int = 3600  # 默认1小时过期

    def __init__(self, user_input: str, input_type: str = "text", ttl_seconds: int = 3600):
        self.request_id = f"req_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        self.user_id: Optional[str] = None
        self.input_type = input_type
        self.user_input = user_input
        self.module_results: dict[str, ModuleContextSchema] = {}
        self.created_at = datetime.now()
        self.expires_at = datetime.now() + timedelta(seconds=ttl_seconds)
        self.meta = {
            "request_id": self.request_id,
            "module_version": "1.0.0",
            "timestamp": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
        }
        # 注册到全局实例表
        with ContextManager._lock:
            ContextManager._instances[self.request_id] = self

    @classmethod
    def create(cls, user_input: str, input_type: str = "text", ttl_seconds: int = 3600) -> "ContextManager":
        """创建新的请求上下文"""
        return cls(user_input, input_type, ttl_seconds)

    @classmethod
    def get(cls, request_id: str) -> Optional["ContextManager"]:
        """根据 request_id 获取上下文"""
        ctx = cls._instances.get(request_id)
        if ctx and not ctx.is_expired():
            return ctx
        return None

    @classmethod
    def cleanup_expired(cls) -> int:
        """清理所有过期上下文，返回清理数量"""
        cleaned = 0
        with cls._lock:
            expired_ids = [
                rid for rid, ctx in cls._instances.items()
                if ctx.is_expired()
            ]
            for rid in expired_ids:
                del cls._instances[rid]
                cleaned += 1
        return cleaned

    @classmethod
    def get_active_count(cls) -> int:
        """获取当前活跃上下文数量"""
        cls.cleanup_expired()
        return len(cls._instances)

    def is_expired(self) -> bool:
        """检查当前上下文是否过期"""
        return datetime.now() > self.expires_at

    def set_module_result(self, module_id: str, result: ModuleContextSchema):
        """设置模块处理结果"""
        result.created_at = datetime.now()
        self.module_results[module_id] = result

    def get_module_result(self, module_id: str) -> Optional[ModuleContextSchema]:
        """获取模块处理结果"""
        return self.module_results.get(module_id)

    def get_upstream_status(self, module_id: str) -> str:
        """检查上游依赖模块的状态"""
        result = self.module_results.get(module_id)
        if result is None:
            return ModuleStatus.UNUSED.value
        return result.status.value if isinstance(result.status, ModuleStatus) else result.status

    def get_upstream_output(self, module_id: str) -> Optional[dict]:
        """安全获取上游模块输出，未处理返回 None"""
        result = self.module_results.get(module_id)
        if result:
            status_val = result.status.value if isinstance(result.status, ModuleStatus) else result.status
            if status_val in ("success", "partial"):
                return result.output
        return None

    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            "request_id": self.request_id,
            "input_type": self.input_type,
            "module_results": {
                k: {
                    "module_id": v.module_id,
                    "status": v.status.value if isinstance(v.status, ModuleStatus) else v.status,
                    "error_info": v.error_info,
                }
                for k, v in self.module_results.items()
            },
            "meta": self.meta,
        }
