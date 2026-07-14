"""正则规则引擎 — 管理所有日志识别规则"""

import re
import os
from dataclasses import dataclass, field
from typing import Optional

from common.logger import LogManager

logger = LogManager.get_logger()


@dataclass
class Rule:
    """单条规则定义"""
    name: str
    patterns: list[re.Pattern] = field(default_factory=list)
    priority: int = 0          # 数值越大优先级越高
    hazard_level: str = "low"  # "high" | "medium" | "low"
    device_type: str = ""
    field_mappings: dict = field(default_factory=dict)


@dataclass
class RuleMatchResult:
    """规则匹配结果"""
    rule: Rule
    matched_text: str
    confidence: float = 1.0


class RegexRuleEngine:
    """正则规则引擎 — 管理所有日志识别规则，支持热加载"""

    rules: list[Rule] = []
    _loaded = False

    @classmethod
    def load_rules(cls, rules_dir: str = None) -> None:
        """从目录加载所有规则文件，按优先级排序"""
        if rules_dir is None:
            try:
                from app.settings import settings
                rules_dir = settings.rule_data_dir
            except ImportError:
                rules_dir = "./data/rule_data"
        cls.rules = []
        if not os.path.isdir(rules_dir):
            logger.warning(f"规则目录不存在: {rules_dir}")
            return

        for filename in sorted(os.listdir(rules_dir)):
            if not filename.endswith((".yaml", ".yml", ".json", ".txt")):
                continue
            filepath = os.path.join(rules_dir, filename)
            cls._load_rule_file(filepath)

        cls.rules.sort(key=lambda r: r.priority, reverse=True)
        cls._loaded = True
        logger.info(f"已加载 {len(cls.rules)} 条规则")

    @classmethod
    def _load_rule_file(cls, filepath: str):
        """加载单个规则文件"""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            logger.error(f"读取规则文件失败 {filepath}: {e}")
            return

        # 简单规则格式：每行一条规则，格式: device_type|priority|hazard_level|regex_pattern
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("//"):
                continue
            parts = line.split("|", 3)
            if len(parts) < 4:
                continue
            device_type, priority_str, hazard_level, pattern_str = parts
            try:
                pattern = re.compile(pattern_str, re.IGNORECASE)
                rule = Rule(
                    name=f"{device_type}_{pattern_str[:20]}",
                    patterns=[pattern],
                    priority=int(priority_str),
                    hazard_level=hazard_level,
                    device_type=device_type,
                    field_mappings={"device_type": device_type},
                )
                cls.rules.append(rule)
            except re.error as e:
                logger.error(f"正则编译失败 [{filepath}]: {pattern_str} - {e}")

    @classmethod
    def match(cls, text: str) -> Optional[RuleMatchResult]:
        """逐级匹配规则，返回第一条命中的规则"""
        if not cls._loaded:
            cls.load_rules()
        for rule in cls.rules:
            for pattern in rule.patterns:
                match = pattern.search(text)
                if match:
                    return RuleMatchResult(rule=rule, matched_text=match.group(0))
        return None

    @classmethod
    def reload(cls):
        """重新加载所有规则"""
        cls._loaded = False
        cls.load_rules()