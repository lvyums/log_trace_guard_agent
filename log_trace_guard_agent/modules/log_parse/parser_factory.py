"""解析器工厂 — 标准化策略模式分发，零侵入扩展"""

from typing import Optional, Type, Dict

from modules.log_parse.base_parser import BaseParser
from modules.log_parse.ssh_parse import SSHParser
from modules.log_parse.web_parse import WebParser
from modules.log_parse.waf_parse import WAFParser
from modules.log_parse.firewall_parse import FirewallParser
from modules.log_parse.db_parse import DBParser
from core.rule_engine.regex_rule import RegexRuleEngine, RuleMatchResult
from common.logger import LogManager

logger = LogManager.get_logger()


class LogParserFactory:
    """解析器工厂 — 注册解析器并按需分发
    新增日志类型只需: 1. 新建解析器类继承 BaseParser  2. 调用 register() 注册
    上层路由、service 层无需任何改动
    """

    _parsers: Dict[str, Type[BaseParser]] = {}
    _device_type_aliases: Dict[str, str] = {}  # 别名映射

    @classmethod
    def register(cls, device_type: str, parser_cls: Type[BaseParser], aliases: list[str] = None):
        """注册解析器到工厂
        Args:
            device_type: 设备类型标识
            parser_cls: 解析器类
            aliases: 可选别名列表，用于兼容不同命名
        """
        cls._parsers[device_type] = parser_cls
        if aliases:
            for alias in aliases:
                cls._device_type_aliases[alias] = device_type
        logger.info(f"注册解析器: {device_type} -> {parser_cls.__name__}")

    @classmethod
    def get_parser(cls, log_line: str) -> Optional[BaseParser]:
        """通过规则引擎 + 多特征匹配，返回对应解析器"""
        # 1. 规则引擎优先匹配
        match_result: Optional[RuleMatchResult] = RegexRuleEngine.match(log_line)
        if match_result:
            raw_type = match_result.rule.device_type
            # 解析别名
            device_type = cls._device_type_aliases.get(raw_type, raw_type)
            parser_cls = cls._parsers.get(device_type)
            if parser_cls:
                return parser_cls()

        # 2. 规则引擎未命中，逐个尝试（can_parse 兜底）
        for device_type, parser_cls in cls._parsers.items():
            parser = parser_cls()
            if parser.can_parse(log_line):
                return parser

        return None

    @classmethod
    def parse(cls, log_line: str) -> Optional[dict]:
        """全自动：识别类型 → 提取字段 → 返回结构化结果"""
        parser = cls.get_parser(log_line)
        if parser is None:
            logger.warning(f"无法识别日志类型: {log_line[:50]}")
            return None
        fields = parser.parse_fields(log_line)
        return fields.model_dump()

    @classmethod
    def get_registered_types(cls) -> list[str]:
        """获取所有已注册的设备类型"""
        return list(cls._parsers.keys())

    @classmethod
    def unregister(cls, device_type: str):
        """注销解析器（用于测试/动态管理）"""
        cls._parsers.pop(device_type, None)
        logger.info(f"注销解析器: {device_type}")


# 注册默认解析器
LogParserFactory.register("ssh", SSHParser)
LogParserFactory.register("web", WebParser)
LogParserFactory.register("waf", WAFParser)
LogParserFactory.register("firewall", FirewallParser)
LogParserFactory.register("db", DBParser)