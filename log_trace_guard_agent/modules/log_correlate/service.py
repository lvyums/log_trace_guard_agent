"""
模块六：日志联合审查 — 多源日志关联分析

提供跨源日志关联分析基础设施：
  - TimelineBuilder: 解析并按时间排序多源日志
  - ChainAnalyzer: 从关联时间线检测攻击链模式
  - LogCorrelateService: 日志联合审查的高层 API

复用已有的 LogParseService 进行单条日志解析和风险研判。
"""

import json
import os
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

from modules.log_parse.service import LogParseService
from core.context_manager import ContextManager
from common.json_util import JsonConfigLoader
from common.logger import LogManager
from common.result_util import Result
from app.settings import settings

logger = LogManager.get_logger()

# 规则文件路径
CORRELATION_PATTERNS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data", "rule_data", "correlation_patterns.json"
)


# ---------------------------------------------------------------------------
# CorrelatedEvent — 时间线上的单个事件
# ---------------------------------------------------------------------------

@dataclass
class CorrelatedEvent:
    """A single parsed event on the correlation timeline."""

    timestamp: Optional[str] = None
    device_type: str = "unknown"
    src_ip: Optional[str] = None
    dst_ip: Optional[str] = None
    user: Optional[str] = None
    status: Optional[str] = None
    command: Optional[str] = None
    raw_log: str = ""
    risk_level: Optional[str] = None
    risk_desc: Optional[str] = None
    extra_info: Dict[str, Any] = field(default_factory=dict)
    line_number: int = 0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None and v != "" and v != {} and v != 0}

    def matches_device_type(self, device_type: str) -> bool:
        return self.device_type == device_type

    def matches_status(self, status: str) -> bool:
        return self.status == status

    def matches_status_prefix(self, prefixes: List[str]) -> bool:
        if not self.status:
            return False
        return any(self.status.startswith(p) for p in prefixes)

    def matches_command(self, keywords: List[str]) -> bool:
        if not self.command:
            return False
        cmd_lower = self.command.lower()
        return any(kw.lower() in cmd_lower for kw in keywords)

    def get_entity_key(self) -> str:
        """获取实体键（用于分组）：src_ip > user > device"""
        if self.src_ip:
            return self.src_ip
        if self.user:
            return self.user
        return self.device_type or "unknown"


# ---------------------------------------------------------------------------
# AttackChain — 检测到的攻击链结果
# ---------------------------------------------------------------------------

@dataclass
class AttackChain:
    """A detected attack chain from correlated events."""

    chain_id: str = ""
    chain_name: str = ""
    description: str = ""
    risk_level: str = "P3_低风险"
    confidence: float = 0.0
    matched_events: List[CorrelatedEvent] = field(default_factory=list)
    matched_stages: List[str] = field(default_factory=list)
    indicators: List[str] = field(default_factory=list)
    suggestion: str = ""
    entity_key: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "chain_name": self.chain_name,
            "description": self.description,
            "risk_level": self.risk_level,
            "confidence": round(self.confidence, 4),
            "matched_stages": self.matched_stages,
            "event_count": len(self.matched_events),
            "indicators": self.indicators,
            "suggestion": self.suggestion,
            "entity_key": self.entity_key,
        }

    def to_dict_detailed(self) -> Dict[str, Any]:
        d = self.to_dict()
        d["events"] = [e.to_dict() for e in self.matched_events]
        return d


# ---------------------------------------------------------------------------
# 时间戳解析
# ---------------------------------------------------------------------------

_RE_ISO = re.compile(r"(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})")
_RE_SYSLOG = re.compile(r"(\w{3})\s+(\d{1,2})\s+(\d{2}):(\d{2}):(\d{2})")
_RE_WEB = re.compile(r"(\d{2})/(\w{3})/(\d{4}):(\d{2}):(\d{2}):(\d{2})")
_RE_ISO_FULL = re.compile(r"(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})")

_MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _parse_timestamp(ts_str: Optional[str]) -> Optional[datetime]:
    """尝试将时间戳字符串解析为 datetime 对象。"""
    if not ts_str or not ts_str.strip():
        return None

    ts_str = ts_str.strip()

    m = _RE_ISO_FULL.match(ts_str)
    if m:
        try:
            return datetime.fromisoformat(m.group(1))
        except (ValueError, TypeError):
            pass

    m = _RE_ISO.match(ts_str)
    if m:
        try:
            return datetime(
                int(m.group(1)), int(m.group(2)), int(m.group(3)),
                int(m.group(4)), int(m.group(5)), int(m.group(6)),
            )
        except (ValueError, TypeError):
            pass

    m = _RE_WEB.match(ts_str)
    if m:
        try:
            month = _MONTH_MAP.get(m.group(2).lower())
            if month:
                return datetime(
                    int(m.group(3)), month, int(m.group(1)),
                    int(m.group(4)), int(m.group(5)), int(m.group(6)),
                )
        except (ValueError, TypeError):
            pass

    m = _RE_SYSLOG.match(ts_str)
    if m:
        try:
            month = _MONTH_MAP.get(m.group(1).lower())
            if month:
                now = datetime.now()
                return datetime(
                    now.year, month, int(m.group(2)),
                    int(m.group(3)), int(m.group(4)), int(m.group(5)),
                )
        except (ValueError, TypeError):
            pass

    return None


# ---------------------------------------------------------------------------
# TimelineBuilder
# ---------------------------------------------------------------------------

class TimelineBuilder:
    """从多条日志条目构建统一时间线。"""

    def __init__(self, time_window_minutes: int = 5):
        self.time_window_minutes = time_window_minutes

    async def build_timeline(
        self,
        log_lines: List[str],
        context: ContextManager,
    ) -> Tuple[List[CorrelatedEvent], Dict[str, List[CorrelatedEvent]]]:
        """从原始日志行构建时间线。"""
        events: List[CorrelatedEvent] = []

        for i, line in enumerate(log_lines, 1):
            line = line.strip()
            if not line:
                continue

            parse_result = await LogParseService.parse_log(line, context)
            if parse_result["code"] != 0:
                logger.warning(f"解析日志行 {i} 失败: {parse_result['msg']}")
                continue
            parsed = parse_result["data"]

            risk_result = await LogParseService.assess_risk(parsed, context)
            risk_data = risk_result["data"] if risk_result["code"] == 0 else {}

            event = CorrelatedEvent(
                timestamp=parsed.get("timestamp"),
                device_type=parsed.get("device_type") or "unknown",
                src_ip=parsed.get("src_ip"),
                dst_ip=parsed.get("dst_ip"),
                user=parsed.get("user"),
                status=parsed.get("status"),
                command=parsed.get("command"),
                raw_log=line,
                risk_level=risk_data.get("risk_level", "P3_噪音"),
                risk_desc=risk_data.get("risk_desc", ""),
                extra_info=parsed.get("extra_info", {}),
                line_number=i,
            )
            events.append(event)

        def _sort_key(e: CorrelatedEvent) -> tuple:
            dt = _parse_timestamp(e.timestamp)
            if dt is None:
                return (1, e.line_number)
            return (0, dt.timestamp(), e.line_number)

        events.sort(key=_sort_key)

        groups: Dict[str, List[CorrelatedEvent]] = {}
        for evt in events:
            key = evt.get_entity_key()
            if key not in groups:
                groups[key] = []
            groups[key].append(evt)

        return events, groups

    def get_time_window(self) -> timedelta:
        return timedelta(minutes=self.time_window_minutes)


# ---------------------------------------------------------------------------
# ChainAnalyzer — 基于关键词的攻击链检测
# ---------------------------------------------------------------------------

class ChainAnalyzer:
    """分析时间线中的攻击链模式。

    从 correlation_patterns.json 加载攻击链规则（基于关键词匹配的格式），
    在时间线中匹配已知攻击链模式。
    """

    _SEVERITY_MAP = {
        "critical": "P0_高危",
        "major": "P1_中危",
        "warning": "P2_低危",
    }

    def __init__(self):
        self._rules: List[dict] = []
        self._load_rules()

    def _load_rules(self):
        """从 JSON 规则文件加载攻击链规则。"""
        try:
            data = JsonConfigLoader.load(CORRELATION_PATTERNS_PATH)
            self._rules = data.get("rules", []) if data else []
        except (FileNotFoundError, ValueError, Exception) as e:
            logger.warning(f"加载 correlation_patterns.json 失败: {e}")
            self._rules = []

    @property
    def patterns(self) -> List[dict]:
        return list(self._rules)

    def analyze(
        self,
        timeline: List[CorrelatedEvent],
        entity_groups: Dict[str, List[CorrelatedEvent]],
        time_window: timedelta,
    ) -> List[AttackChain]:
        """分析时间线中的攻击链模式。

        对于每条规则，在每个实体组内匹配关键词模式。
        返回按置信度降序排列的攻击链列表。
        """
        results: List[AttackChain] = []

        if not self._rules or not timeline:
            return results

        for rule in self._rules:
            rule_patterns = rule.get("patterns", [])
            if not rule_patterns:
                continue

            for entity_key, group_events in entity_groups.items():
                chain = self._match_rule_in_group(
                    rule=rule,
                    rule_patterns=rule_patterns,
                    events=group_events,
                    entity_key=entity_key,
                )
                if chain is not None:
                    results.append(chain)

        # 按置信度降序排序
        results.sort(key=lambda c: c.confidence, reverse=True)

        # 去重：相同 chain_name + entity_key 保留最高置信度
        seen: set = set()
        deduped: List[AttackChain] = []
        for chain in results:
            dedup_key = (chain.chain_name, chain.entity_key)
            if dedup_key not in seen:
                seen.add(dedup_key)
                deduped.append(chain)

        return deduped

    def _match_rule_in_group(
        self,
        rule: dict,
        rule_patterns: List[dict],
        events: List[CorrelatedEvent],
        entity_key: str,
    ) -> Optional[AttackChain]:
        """在实体组中匹配一条规则的所有关键词模式。"""
        rule_name = rule.get("name", "")
        rule_time_window_sec = rule.get("time_window", 300)
        rule_time_window = timedelta(seconds=rule_time_window_sec)
        required_matches = rule.get("required_matches", 2)
        min_freq = rule.get("min_freq", 1)

        # 对每个模式，找到匹配的事件
        matched_patterns: List[dict] = []  # 匹配的模式索引
        pattern_matched_events: Dict[int, List[CorrelatedEvent]] = {}  # 模式索引 -> 匹配事件列表

        for p_idx, pattern in enumerate(rule_patterns):
            matching_events = self._find_events_for_pattern(pattern, events, rule_time_window)
            if len(matching_events) >= min_freq:
                matched_patterns.append(pattern)
                pattern_matched_events[p_idx] = matching_events

        # 检查是否满足 required_matches
        if len(matched_patterns) < required_matches:
            return None

        # 收集所有匹配事件（去重）
        all_matched_events: List[CorrelatedEvent] = []
        seen_event_ids: Set[int] = set()
        for p_idx in pattern_matched_events:
            for evt in pattern_matched_events[p_idx]:
                if evt.line_number not in seen_event_ids:
                    seen_event_ids.add(evt.line_number)
                    all_matched_events.append(evt)

        if not all_matched_events:
            return None

        # 计算置信度
        total_patterns = len(rule_patterns)
        matched_count = len(matched_patterns)
        confidence = matched_count / total_patterns if total_patterns > 0 else 0.0

        # 提取指标
        indicators = []
        for evt in all_matched_events:
            if evt.risk_desc:
                indicators.append(evt.risk_desc)
            if evt.src_ip and f"源IP: {evt.src_ip}" not in indicators:
                indicators.append(f"源IP: {evt.src_ip}")
            if evt.user and f"用户: {evt.user}" not in indicators:
                indicators.append(f"用户: {evt.user}")

        severity = rule.get("severity", "warning")
        risk_level = self._SEVERITY_MAP.get(severity, "P3_低风险")

        chain = AttackChain(
            chain_id=rule_name,
            chain_name=rule_name,
            description=rule.get("description", ""),
            risk_level=risk_level,
            confidence=confidence,
            matched_events=all_matched_events,
            matched_stages=[f"模式 {i+1}" for i in range(len(matched_patterns))],
            indicators=indicators[:10],
            suggestion=self._get_suggestion(rule),
            entity_key=entity_key,
        )

        return chain

    def _find_events_for_pattern(
        self,
        pattern: dict,
        events: List[CorrelatedEvent],
        time_window: timedelta,
    ) -> List[CorrelatedEvent]:
        """在事件列表中查找匹配指定关键词模式的事件。"""
        keyword = pattern.get("keyword", "")
        source = pattern.get("source", ".*")

        if not keyword:
            return []

        # 关键词本身是正则模式（如 "rollback|abort"、"failed to.*"）
        try:
            keyword_re = re.compile(keyword, re.IGNORECASE)
        except re.error:
            return []

        # 构建 source/device_type 匹配正则
        try:
            source_re = re.compile(source, re.IGNORECASE) if source != ".*" else None
        except re.error:
            source_re = None

        matching_events = []
        for event in events:
            # 关键词匹配（在 raw_log 中搜索）
            if not event.raw_log or not keyword_re.search(event.raw_log):
                continue

            # source 匹配（设备类型过滤）：unknown/空类型不拦截，减少漏报
            if source_re is not None:
                dt = event.device_type or "unknown"
                if dt != "unknown" and not source_re.search(dt):
                    continue

            matching_events.append(event)

        # 如果匹配事件超过 1 个，检查时间窗口
        if len(matching_events) > 1:
            # 按时间戳排序
            def _ts_key(e):
                dt = _parse_timestamp(e.timestamp)
                return dt.timestamp() if dt else 0

            matching_events.sort(key=_ts_key)
            # 检查第一个和最后一个的时间差
            first_ts = _parse_timestamp(matching_events[0].timestamp)
            last_ts = _parse_timestamp(matching_events[-1].timestamp)
            if first_ts and last_ts and (last_ts - first_ts) > time_window:
                # 只保留时间窗口内的事件
                windowed = [matching_events[0]]
                for evt in matching_events[1:]:
                    evt_ts = _parse_timestamp(evt.timestamp)
                    if evt_ts and (evt_ts - first_ts) <= time_window:
                        windowed.append(evt)
                return windowed

        return matching_events

    @staticmethod
    def _get_suggestion(rule: dict) -> str:
        """根据规则生成处置建议。"""
        severity = rule.get("severity", "warning")
        name = rule.get("name", "")
        suggestions = {
            "brute_force_attempt_chain": "立即封禁攻击源IP，检查被爆破的账户是否被成功登录，修改密码并启用多因素认证。",
            "out_of_memory_chain": "检查内存使用率，评估是否需要扩容或优化内存泄漏的应用。",
            "connection_refused_chain": "检查目标服务是否正常运行，确认端口是否已监听，重启服务或排查服务崩溃原因。",
            "pod_crashloop_chain": "检查容器日志定位启动失败原因，修复后重新部署。",
            "service_dependency_cascade": "检查上游服务状态，评估依赖关系，启用熔断机制防止级联故障。",
        }
        for key, suggestion in suggestions.items():
            if key in name:
                return suggestion
        if severity == "critical":
            return "立即排查并修复，防止进一步损失。"
        elif severity == "major":
            return "尽快排查，评估影响范围。"
        return "持续监控，必要时升级处理。"


# ---------------------------------------------------------------------------
# LogCorrelateService — 高层 API
# ---------------------------------------------------------------------------

class LogCorrelateService:
    """日志联合审查高层服务。"""

    _chain_analyzer: Optional[ChainAnalyzer] = None

    @classmethod
    def _get_analyzer(cls) -> ChainAnalyzer:
        if cls._chain_analyzer is None:
            cls._chain_analyzer = ChainAnalyzer()
        return cls._chain_analyzer

    @classmethod
    async def correlate_logs(
        cls,
        log_lines: List[str],
        context: ContextManager,
        time_window_minutes: int = 5,
        detailed: bool = False,
    ) -> dict:
        """分析多条日志进行关联检测。"""
        if not log_lines:
            return Result.ok({
                "total_events": 0,
                "device_types": [],
                "entities": [],
                "chains": [],
                "summary": "没有日志可供分析",
            })

        builder = TimelineBuilder(time_window_minutes)
        time_window = builder.get_time_window()
        timeline, entity_groups = await builder.build_timeline(log_lines, context)

        if not timeline:
            return Result.ok({
                "total_events": 0,
                "device_types": [],
                "entities": [],
                "chains": [],
                "summary": "未能解析任何日志行",
            })

        analyzer = cls._get_analyzer()
        chains = analyzer.analyze(timeline, entity_groups, time_window)

        device_types = sorted(set(e.device_type for e in timeline if e.device_type and e.device_type != "unknown"))
        entities = sorted(set(e.get_entity_key() for e in timeline))

        if chains:
            high_risk = [c for c in chains if c.risk_level.startswith("P0")]
            chain_summary_parts = [f"检测到 {len(chains)} 条攻击链"]
            if high_risk:
                chain_summary_parts.append(f"其中 {len(high_risk)} 条高危")
            chain_summary = "，".join(chain_summary_parts)
        else:
            chain_summary = "未检测到已知攻击链模式"

        summary = (
            f"共解析 {len(timeline)} 条日志，涉及 {len(device_types)} 种设备类型"
            f"（{', '.join(device_types)}），{len(entities)} 个实体。"
            f"{chain_summary}。"
        )

        result = {
            "total_events": len(timeline),
            "device_types": device_types,
            "entities": entities,
            "chains": [c.to_dict() for c in chains],
            "summary": summary,
        }

        if detailed:
            result["timeline"] = [e.to_dict() for e in timeline]
            result["chains_detailed"] = [c.to_dict_detailed() for c in chains]

        return Result.ok(result)

    @classmethod
    def get_available_patterns(cls) -> List[dict]:
        """返回可用攻击链模式列表（用于展示）。"""
        analyzer = cls._get_analyzer()
        return [
            {
                "id": p.get("name"),
                "name": p.get("name"),
                "risk_level": cls._SEVERITY_MAP.get(p.get("severity", ""), "P3_低风险"),
                "stages": [pp.get("keyword", "") for pp in p.get("patterns", [])],
            }
            for p in analyzer.patterns
        ]

    _SEVERITY_MAP = {
        "critical": "P0_高危",
        "major": "P1_中危",
        "warning": "P2_低危",
    }