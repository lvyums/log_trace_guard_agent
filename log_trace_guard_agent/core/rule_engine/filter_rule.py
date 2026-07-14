"""日志降噪过滤器 — 过滤低价值/重复日志"""

import re
from typing import Optional

from common.logger import LogManager

logger = LogManager.get_logger()

# 默认降噪规则
FILTER_PATTERNS = [
    re.compile(r"heartbeat", re.IGNORECASE),
    re.compile(r"keep-alive", re.IGNORECASE),
    re.compile(r"^$"),  # 空行
]


class FilterRuleEngine:
    """日志降噪过滤器"""

    _patterns: list[re.Pattern] = FILTER_PATTERNS.copy()

    @classmethod
    def should_filter(cls, log_line: str) -> bool:
        """判断日志是否属于降噪范围"""
        for pattern in cls._patterns:
            if pattern.search(log_line):
                return True
        return False

    @classmethod
    def add_filter(cls, pattern: re.Pattern):
        """添加自定义过滤规则"""
        cls._patterns.append(pattern)

    @classmethod
    def clear_filters(cls):
        """清空所有过滤规则"""
        cls._patterns.clear()