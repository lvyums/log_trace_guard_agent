"""日志联合审查 — 请求/响应模型"""

from pydantic import BaseModel, Field
from typing import Optional


class CorrelateLogsReq(BaseModel):
    """日志关联分析请求"""
    log_lines: list[str] = Field(default_factory=list, min_length=1, description="日志行列表")
    time_window_minutes: int = Field(default=5, ge=1, le=1440, description="关联时间窗口（分钟）")
    detailed: bool = Field(default=False, description="是否返回详细时间线")


class CorrelateResp(BaseModel):
    """日志关联分析响应"""
    total_events: int = Field(default=0, description="总事件数")
    device_types: list[str] = Field(default_factory=list, description="设备类型列表")
    entities: list[str] = Field(default_factory=list, description="实体列表")
    chains: list[dict] = Field(default_factory=list, description="攻击链列表")
    summary: str = Field(default="", description="分析摘要")


class PatternItem(BaseModel):
    """攻击链模式条目"""
    id: Optional[str] = None
    name: str = ""
    risk_level: str = ""
    stages: list[str] = Field(default_factory=list)


class PatternListResp(BaseModel):
    """攻击链模式列表响应"""
    patterns: list[PatternItem] = Field(default_factory=list)
