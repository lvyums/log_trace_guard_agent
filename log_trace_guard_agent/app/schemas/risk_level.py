"""风险等级枚举 — 全项目统一引用"""

from enum import Enum


class RiskLevel(str, Enum):
    """风险等级枚举"""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"