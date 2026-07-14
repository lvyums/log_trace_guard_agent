"""日志解析器基类"""

from abc import ABC, abstractmethod
from typing import Optional


class BaseParser(ABC):
    """解析器基类 — 所有日志解析器继承此类"""

    device_type: str = "unknown"

    @abstractmethod
    def can_parse(self, log_line: str) -> bool:
        """判断是否能解析该日志"""
        ...

    @abstractmethod
    def parse_fields(self, log_line: str) -> dict:
        """提取结构化字段
        返回: {timestamp, src_ip, dst_ip, src_port, dst_port, user, url, method, command, status, device_type}
        """
        ...

    def validate(self, parsed: dict) -> dict:
        """标记缺失字段，保证输出完整性"""
        required_fields = ["timestamp", "src_ip", "dst_ip", "user", "status", "device_type"]
        for field in required_fields:
            if field not in parsed or parsed[field] is None:
                parsed[f"{field}_missing"] = True
        return parsed