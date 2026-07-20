"""事件风险等级枚举 — 用于攻击链路/事件分析模块

注意：与 app.settings.RiskLevel（P0-P3 合规风险等级）是不同维度的枚举。
- EventRiskLevel: 事件严重度（info/low/medium/high），用于 trace_link 等攻击分析
- settings.RiskLevel: 合规风险等级（P0_高危 ~ P3_噪音），用于日志解析/关联分析
"""

from enum import Enum


class EventRiskLevel(str, Enum):
    """事件风险等级（攻击链路/事件分析用）"""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# 向后兼容别名
RiskLevel = EventRiskLevel
