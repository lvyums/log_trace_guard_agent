"""模块四：脚本生成策略抽象基类 + 工厂注册模式"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type

from common.logger import LogManager

logger = LogManager.get_logger()


class BaseScriptStrategy(ABC):
    """脚本生成策略基类 — 所有策略继承此类"""

    strategy_type: str = "unknown"
    strategy_name: str = "unknown"

    @abstractmethod
    def generate(self, params: dict) -> dict:
        """执行策略生成逻辑"""
        ...

    @abstractmethod
    def can_handle(self, params: dict) -> bool:
        """判断是否能处理该场景"""
        ...


class ScriptStrategyFactory:
    """脚本策略工厂 — 注册模式，零侵入扩展"""

    _strategies: Dict[str, Type[BaseScriptStrategy]] = {}

    @classmethod
    def register(cls, strategy_type: str, strategy_cls: Type[BaseScriptStrategy]):
        """注册策略类"""
        cls._strategies[strategy_type] = strategy_cls
        logger.info(f"注册脚本策略: {strategy_type} -> {strategy_cls.__name__}")

    @classmethod
    def get_strategy(cls, strategy_type: str) -> Optional[BaseScriptStrategy]:
        """获取策略实例"""
        strategy_cls = cls._strategies.get(strategy_type)
        if strategy_cls:
            return strategy_cls()
        return None

    @classmethod
    def get_all_types(cls) -> list[str]:
        """获取所有已注册策略类型"""
        return list(cls._strategies.keys())

    @classmethod
    def unregister(cls, strategy_type: str):
        """注销策略（用于测试）"""
        cls._strategies.pop(strategy_type, None)