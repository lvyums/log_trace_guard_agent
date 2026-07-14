"""跨模块调用抽象接口层 — 模块间解耦依赖

五大业务模块禁止互相 import，通过此抽象层调用其它模块能力。
后续实训、合规模块如需调用日志解析能力，仅依赖此抽象接口。
"""

from abc import ABC, abstractmethod
from typing import Optional


class AbstractLogParseService(ABC):
    """日志解析抽象服务 — 跨模块调用接口"""

    @abstractmethod
    async def identify_log_type(self, log_line: str) -> dict:
        """识别日志类型"""
        ...

    @abstractmethod
    async def parse_log(self, log_line: str) -> dict:
        """解析日志"""
        ...

    @abstractmethod
    async def assess_risk(self, parsed_fields: dict) -> dict:
        """风险研判"""
        ...