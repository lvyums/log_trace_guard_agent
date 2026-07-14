"""模块三: 日志采集架构指导模块

架构: 工厂模式 + 策略模式 + 外部配置驱动
- collect_strategy: 采集策略工厂（外部注册，零硬编码）
- device_match: 设备匹配器（外部配置 + 置信度评估）
- fault_fix: 故障诊断器（外部知识库 + 多维度联合匹配）
- service: 业务编排（参数校验 + RAG增强 + 批量支持）
- router: API 路由（6个接口）
"""

from modules.log_collect.collect_strategy import CollectStrategyFactory
from modules.log_collect.service import LogCollectService
from modules.log_collect.router import router

__all__ = ["CollectStrategyFactory", "LogCollectService", "router"]
