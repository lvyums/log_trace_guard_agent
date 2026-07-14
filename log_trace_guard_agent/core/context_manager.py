"""模块间上下文传递管理"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class ModuleContext:
    """单个模块的处理上下文"""
    module_id: str
    status: str = "unused"  # "unused" | "success" | "partial" | "warning" | "error"
    input: dict = field(default_factory=dict)
    output: Optional[dict] = None
    error_info: Optional[str] = None


class ContextManager:
    """模块间上下文传递 — 管理请求全链路的模块状态和数据"""

    def __init__(self, user_input: str, input_type: str = "text"):
        self.request_id = f"req_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        self.user_id: Optional[str] = None
        self.input_type = input_type
        self.user_input = user_input
        self.module_results: dict[str, ModuleContext] = {}
        self.meta = {
            "request_id": self.request_id,
            "module_version": "1.0.0",
            "timestamp": datetime.now().isoformat(),
        }

    @classmethod
    def create(cls, user_input: str, input_type: str = "text") -> "ContextManager":
        """创建新的请求上下文"""
        return cls(user_input, input_type)

    def set_module_result(self, module_id: str, result: ModuleContext):
        """设置模块处理结果"""
        self.module_results[module_id] = result

    def get_module_result(self, module_id: str) -> Optional[ModuleContext]:
        """获取模块处理结果"""
        return self.module_results.get(module_id)

    def get_upstream_status(self, module_id: str) -> str:
        """检查上游依赖模块的状态"""
        result = self.module_results.get(module_id)
        if result is None:
            return "unused"
        return result.status

    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            "request_id": self.request_id,
            "input_type": self.input_type,
            "module_results": {
                k: {
                    "module_id": v.module_id,
                    "status": v.status,
                    "error_info": v.error_info,
                }
                for k, v in self.module_results.items()
            },
            "meta": self.meta,
        }