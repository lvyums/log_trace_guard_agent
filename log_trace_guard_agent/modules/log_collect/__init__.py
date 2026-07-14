"""模块三: 日志采集架构指导模块"""

from modules.log_collect.collect_strategy import CollectStrategyFactory
from modules.log_collect.service import LogCollectService
from modules.log_collect.router import router

__all__ = ["CollectStrategyFactory", "LogCollectService", "router"]
