"""Web 日志解析器（Apache/Nginx 格式 — 支持清洗前后两种格式）"""

import re

from modules.log_parse.base_parser import BaseParser
from common.time_util import parse_log_time


class WebParser(BaseParser):
    """Web 访问日志解析器"""

    device_type = "web"

    # Combined 格式: '192.168.1.1 - - [10/Oct/2023:13:55:36 +0000] "GET /index.html HTTP/1.1" 200 2326 "-" "Mozilla/5.0"'
    COMBINED_PATTERN = re.compile(
        r'([\d.]+)\s+-\s+(\S+)\s+\[([^\]]+)\]\s+"(\S+)\s+(\S+)\s+(\S+)"\s+(\d+)\s+(\d+)\s+"([^"]*)"\s+"([^"]*)"'
    )
    # Common 格式: '192.168.1.1 - frank [10/Oct/2023:13:55:36 +0000] "GET /index.html HTTP/1.1" 200 2326'
    COMMON_PATTERN = re.compile(
        r'([\d.]+)\s+-\s+(\S+)\s+\[([^\]]+)\]\s+"(\S+)\s+(\S+)\s+(\S+)"\s+(\d+)\s+(\d+)'
    )

    def can_parse(self, log_line: str) -> bool:
        return bool(self.COMBINED_PATTERN.search(log_line) or self.COMMON_PATTERN.search(log_line))

    def parse_fields(self, log_line: str) -> dict:
        result = {
            "timestamp": parse_log_time(log_line),
            "src_ip": None,
            "dst_ip": None,
            "src_port": None,
            "dst_port": "80",
            "user": None,
            "url": None,
            "method": None,
            "command": None,
            "status": "unknown",
            "device_type": "web",
            "user_agent": None,
            "body_bytes": None,
            "http_version": None,
        }

        # 尝试 Combined 格式
        match = self.COMBINED_PATTERN.search(log_line)
        if match:
            result["src_ip"] = match.group(1)
            result["user"] = match.group(2) if match.group(2) != "-" else None
            result["timestamp"] = parse_log_time(log_line) or match.group(3)
            result["method"] = match.group(4)
            result["url"] = match.group(5)
            result["http_version"] = match.group(6)
            result["status"] = match.group(7)
            result["body_bytes"] = match.group(8)
            result["user_agent"] = match.group(10)
            return self.validate(result)

        # 尝试 Common 格式
        match = self.COMMON_PATTERN.search(log_line)
        if match:
            result["src_ip"] = match.group(1)
            result["user"] = match.group(2) if match.group(2) != "-" else None
            result["timestamp"] = parse_log_time(log_line) or match.group(3)
            result["method"] = match.group(4)
            result["url"] = match.group(5)
            result["http_version"] = match.group(6)
            result["status"] = match.group(7)
            result["body_bytes"] = match.group(8)
            return self.validate(result)

        return self.validate(result)