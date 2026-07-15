"""风险基线池 — 标准化风险分级 + 规则统一管理（外部配置驱动）"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from common.logger import LogManager
from common.json_util import JsonConfigLoader

logger = LogManager.get_logger()


@dataclass
class RiskRule:
    """单条风险规则"""
    rule_id: str
    name: str
    risk_level: str         # "P0_高危" | "P1_中危" | "P2_低危" | "P3_噪音"
    device_type: str        # "ssh" | "web" | "waf" | "firewall" | "db" | "any"
    condition: dict         # 匹配条件: {"field": "status", "value": "failed", "operator": "eq"}
    weight: float = 1.0     # 权重，用于多特征加权
    confidence: float = 0.9  # 命中时置信度
    attack_type: str = ""
    risk_desc: str = ""
    suggestion: str = ""
    is_active: bool = True


@dataclass
class RiskMatchResult:
    """风险匹配结果"""
    rule_id: str
    risk_level: str
    confidence: float
    attack_type: Optional[str]
    risk_desc: Optional[str]
    suggestion: Optional[str]
    matched_fields: dict = field(default_factory=dict)


class RiskBaseline:
    """风险基线池 — 所有风险规则统一管理，业务代码禁止写死规则"""

    _rules: dict[str, RiskRule] = {}
    _initialized = False

    @classmethod
    def initialize(cls):
        """初始化默认风险规则"""
        if cls._initialized:
            return
        cls._register_default_rules()
        cls._initialized = True
        logger.info(f"风险基线初始化完成，共 {len(cls._rules)} 条规则")

    @classmethod
    def _register_default_rules(cls):
        """从外部 JSON 配置文件加载风险规则"""
        from app.settings import settings
        config_path = f"{settings.rule_data_dir}/risk_rules.json"
        try:
            rules_data = JsonConfigLoader.load(config_path)
            if not rules_data:
                logger.warning(f"风险规则配置为空: {config_path}")
                return
            for item in rules_data:
                rule = RiskRule(
                    rule_id=item["rule_id"],
                    name=item["name"],
                    risk_level=item["risk_level"],
                    device_type=item["device_type"],
                    condition=item["condition"],
                    weight=item.get("weight", 1.0),
                    confidence=item.get("confidence", 0.9),
                    attack_type=item.get("attack_type", ""),
                    risk_desc=item.get("risk_desc", ""),
                    suggestion=item.get("suggestion", ""),
                )
                cls._rules[rule.rule_id] = rule
            logger.info(f"从配置文件加载 {len(rules_data)} 条风险规则: {config_path}")
        except Exception as e:
            logger.error(f"加载风险规则配置失败: {e}")

    @classmethod
    def reload_rules(cls):
        """热加载风险规则配置"""
        cls._rules.clear()
        cls._initialized = False
        cls.initialize()
        logger.info("风险规则配置已热加载")

    @classmethod
    def get_rule(cls, rule_id: str) -> Optional[RiskRule]:
        return cls._rules.get(rule_id)

    @classmethod
    def get_active_rules(cls, device_type: Optional[str] = None) -> list[RiskRule]:
        """获取活跃规则，可按设备类型过滤"""
        rules = [r for r in cls._rules.values() if r.is_active]
        if device_type:
            rules = [r for r in rules if r.device_type == device_type or r.device_type == "any"]
        return rules

    @classmethod
    def register_rule(cls, rule: RiskRule):
        """注册新规则"""
        cls._rules[rule.rule_id] = rule
        logger.info(f"注册风险规则: {rule.rule_id} - {rule.name}")

    @classmethod
    def evaluate(cls, parsed_fields: dict) -> list[RiskMatchResult]:
        """对解析后的字段进行风险匹配，返回所有命中结果"""
        cls.initialize()
        results = []
        device_type = parsed_fields.get("device_type", "")

        for rule in cls.get_active_rules(device_type):
            match = cls._evaluate_rule(rule, parsed_fields)
            if match:
                results.append(match)

        # 按风险等级排序
        level_order = {"P0_高危": 0, "P1_中危": 1, "P2_低危": 2, "P3_噪音": 3}
        results.sort(key=lambda r: level_order.get(r.risk_level, 99))

        return results

    @classmethod
    def _evaluate_rule(cls, rule: RiskRule, parsed_fields: dict) -> Optional[RiskMatchResult]:
        """评估单条规则是否命中"""
        cond = rule.condition
        field = cond.get("field", "")
        value = parsed_fields.get(field)

        # 总是命中的规则（兜底）
        if cond.get("operator") == "always_true":
            return RiskMatchResult(
                rule_id=rule.rule_id,
                risk_level=rule.risk_level,
                confidence=rule.confidence * 100,
                attack_type=rule.attack_type,
                risk_desc=rule.risk_desc,
                suggestion=rule.suggestion,
                matched_fields={field: value},
            )

        if value is None:
            return None

        operator = cond.get("operator", "eq")

        if operator == "eq":
            if value == cond.get("value"):
                return cls._build_match(rule, value, field)

        elif operator == "startswith":
            prefixes = cond.get("value", [])
            if any(str(value).startswith(p) for p in prefixes):
                return cls._build_match(rule, value, field)

        elif operator == "contains_any":
            keywords = cond.get("keywords", [])
            if any(kw in str(value) for kw in keywords):
                return cls._build_match(rule, value, field)

        return None

    @classmethod
    def _build_match(cls, rule: RiskRule, matched_value, field_name: str = "") -> RiskMatchResult:
        return RiskMatchResult(
            rule_id=rule.rule_id,
            risk_level=rule.risk_level,
            confidence=rule.confidence * 100,
            attack_type=rule.attack_type,
            risk_desc=rule.risk_desc,
            suggestion=rule.suggestion,
            matched_fields={field_name or "value": matched_value},
        )

    @classmethod
    def update_rule(cls, rule_id: str, updates: dict) -> None:
        """更新规则"""
        rule = cls._rules.get(rule_id)
        if not rule:
            logger.warning(f"规则不存在: {rule_id}")
            return
        for key, val in updates.items():
            if hasattr(rule, key):
                setattr(rule, key, val)
        logger.info(f"规则 {rule_id} 已更新")