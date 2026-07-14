"""风险基线池 — 标准化风险分级 + 规则统一管理"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from common.logger import LogManager

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
        """注册默认风险规则"""
        defaults = [
            # ── SSH 类 ──
            RiskRule(
                rule_id="SSH-001", name="SSH暴力破解",
                risk_level="P1_中危", device_type="ssh",
                condition={"field": "status", "value": "failed", "operator": "eq"},
                confidence=0.85, attack_type="SSH暴力破解",
                risk_desc="SSH登录失败，可能为密码暴力破解尝试",
                suggestion="建议检查源IP信誉，配置登录失败锁定策略，启用SSH密钥认证",
            ),
            RiskRule(
                rule_id="SSH-002", name="SSH高危命令执行",
                risk_level="P0_高危", device_type="ssh",
                condition={"field": "command", "keywords": ["rm", "wget", "curl", "chmod", "useradd", "passwd", "mv /etc"], "operator": "contains_any"},
                confidence=0.95, attack_type="高危命令执行",
                risk_desc="SSH会话中执行了高危命令，可能为权限维持或后门植入",
                suggestion="立即确认操作人身份，核查命令执行上下文，审计近期登录记录",
            ),
            RiskRule(
                rule_id="SSH-003", name="SSH异常时间登录",
                risk_level="P2_低危", device_type="ssh",
                condition={"field": "status", "value": "success", "operator": "eq"},
                confidence=0.30, attack_type="异常时间登录",
                risk_desc="SSH登录成功，时间异常需结合上下文判断",
                suggestion="建议确认是否为运维人员正常操作",
            ),
            # ── Web 类 ──
            RiskRule(
                rule_id="WEB-001", name="Web敏感路径访问",
                risk_level="P0_高危", device_type="web",
                condition={"field": "url", "keywords": ["wp-admin", "admin.php", "eval", "cmd=", "system(", "exec(", "../", "passwd"], "operator": "contains_any"},
                confidence=0.90, attack_type="Web攻击",
                risk_desc="访问敏感路径，可能为Web攻击或漏洞探测",
                suggestion="建议检查Web日志中同一源IP的其他请求，确认是否存在扫描行为，及时修补漏洞",
            ),
            RiskRule(
                rule_id="WEB-002", name="Web异常状态码",
                risk_level="P1_中危", device_type="web",
                condition={"field": "status", "operator": "startswith", "value": ["4", "5"]},
                confidence=0.70, attack_type="Web异常访问",
                risk_desc="HTTP状态码异常，可能为访问错误或扫描探测",
                suggestion="建议结合URL路径判断是否为正常业务访问",
            ),
            RiskRule(
                rule_id="WEB-003", name="Web扫描探测",
                risk_level="P2_低危", device_type="web",
                condition={"field": "user_agent", "keywords": ["python-requests", "curl", "wget", "nmap", "sqlmap"], "operator": "contains_any"},
                confidence=0.75, attack_type="扫描探测",
                risk_desc="使用自动化工具访问，可能为扫描探测行为",
                suggestion="建议确认源IP是否在已知扫描器列表中",
            ),
            # ── 通用类 ──
            RiskRule(
                rule_id="GEN-001", name="非工作时间活动",
                risk_level="P3_噪音", device_type="any",
                condition={"field": "time_range", "operator": "always_true"},
                confidence=0.10, attack_type="",
                risk_desc="常规日志记录，无异常特征",
                suggestion="",
            ),
        ]
        for rule in defaults:
            cls._rules[rule.rule_id] = rule

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
                return cls._build_match(rule, value)

        elif operator == "startswith":
            prefixes = cond.get("value", [])
            if any(str(value).startswith(p) for p in prefixes):
                return cls._build_match(rule, value)

        elif operator == "contains_any":
            keywords = cond.get("keywords", [])
            if any(kw in str(value) for kw in keywords):
                return cls._build_match(rule, value)

        return None

    @classmethod
    def _build_match(cls, rule: RiskRule, matched_value) -> RiskMatchResult:
        return RiskMatchResult(
            rule_id=rule.rule_id,
            risk_level=rule.risk_level,
            confidence=rule.confidence * 100,
            attack_type=rule.attack_type,
            risk_desc=rule.risk_desc,
            suggestion=rule.suggestion,
            matched_fields={"value": matched_value},
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
        rule.updated_at = datetime.now().isoformat()
        logger.info(f"规则 {rule_id} 已更新")