"""模块间上下文传递 — Pydantic 强类型模型"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class ModuleStatus(str, Enum):
    """模块处理状态枚举"""
    UNUSED = "unused"
    SUCCESS = "success"
    PARTIAL = "partial"
    WARNING = "warning"
    ERROR = "error"


class ModuleContextSchema(BaseModel):
    """单个模块的处理上下文 — 强类型约束"""
    module_id: str = Field(..., max_length=50, description="模块标识")
    status: ModuleStatus = Field(default=ModuleStatus.UNUSED, description="处理状态")
    input: dict = Field(default_factory=dict, description="模块输入")
    output: Optional[dict] = Field(default=None, description="模块输出")
    error_info: Optional[str] = Field(default=None, max_length=2000, description="错误信息")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")

    class Config:
        json_schema_extra = {
            "example": {
                "module_id": "log_collect",
                "status": "success",
                "input": {"device_type": "firewall"},
                "output": {"plan": {"protocol": "syslog"}},
            }
        }


class RequestContextSchema(BaseModel):
    """请求级全链路上下文 — 按 request_id 隔离"""
    request_id: str = Field(..., max_length=100, description="请求唯一ID")
    user_id: Optional[str] = Field(default=None, max_length=100, description="用户ID")
    input_type: str = Field(default="text", pattern="^(text|file|scene)$", description="输入类型")
    user_input: str = Field(default="", max_length=10000, description="用户输入")
    module_results: dict[str, ModuleContextSchema] = Field(default_factory=dict, description="模块结果")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    expires_at: Optional[datetime] = Field(default=None, description="过期时间")

    def is_expired(self, ttl_seconds: int = 3600) -> bool:
        """检查上下文是否过期"""
        if self.expires_at:
            return datetime.now() > self.expires_at
        elapsed = (datetime.now() - self.created_at).total_seconds()
        return elapsed > ttl_seconds

    def get_module_output(self, module_id: str) -> Optional[dict]:
        """安全获取模块输出"""
        ctx = self.module_results.get(module_id)
        if ctx and ctx.status == ModuleStatus.SUCCESS:
            return ctx.output
        return None
