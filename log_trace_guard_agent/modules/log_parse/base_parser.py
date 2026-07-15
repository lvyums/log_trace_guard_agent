"""日志解析器基类"""

from abc import ABC, abstractmethod
from typing import Optional

from pydantic import BaseModel, Field


class ParsedLogFields(BaseModel):
    """解析后的日志字段 — 所有解析器统一返回此模型"""
    timestamp: Optional[str] = None
    src_ip: Optional[str] = None
    dst_ip: Optional[str] = None
    src_port: Optional[str] = None
    dst_port: Optional[str] = None
    user: Optional[str] = None
    url: Optional[str] = None
    method: Optional[str] = None
    command: Optional[str] = None
    status: Optional[str] = None
    device_type: str = "unknown"
    protocol: Optional[str] = None
    action: Optional[str] = None
    user_agent: Optional[str] = None
    sql_statement: Optional[str] = None
    is_dangerous: Optional[bool] = None
    attack_type: Optional[str] = None
    missing_fields: list[str] = Field(default_factory=list)
    raw_log: Optional[str] = None

    model_config = {"extra": "allow"}  # 允许解析器自有字段（如 user_agent）

    def mark_missing(self) -> list[str]:
        """标记缺失字段并返回缺失列表"""
        required = ["timestamp", "src_ip", "user", "status"]
        missing = []
        for field in required:
            value = getattr(self, field, None)
            if value is None:
                missing.append(field)
                setattr(self, f"{field}_missing", True)
        self.missing_fields = missing
        return missing


class BaseParser(ABC):
    """解析器基类 — 所有日志解析器继承此类"""

    device_type: str = "unknown"

    @abstractmethod
    def can_parse(self, log_line: str) -> bool:
        """判断是否能解析该日志"""
        ...

    @abstractmethod
    def parse_fields(self, log_line: str) -> ParsedLogFields:
        """提取结构化字段，返回 ParsedLogFields"""
        ...

    def validate(self, parsed: ParsedLogFields) -> ParsedLogFields:
        """标记缺失字段，保证输出完整性"""
        parsed.mark_missing()
        return parsed