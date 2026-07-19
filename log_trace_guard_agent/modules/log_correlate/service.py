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
from typing import Any, Dict, List, Optional, Tuple

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
        return self.device_type


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

# ISO 8601: 2024-01-01T10:00:00 或 2024-01-01 10:00:00
_RE_ISO = re.compile(r"(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})")
# Syslog: Jan 15 10:30:00
_RE_SYSLOG = re.compile(r"(\w{3})\s+(\d{1,2})\s+(\d{2}):(\d{2}):(\d{2})")
# Web: 15/Jan/2024:10:30:00
_RE_WEB = re.compile(r"(\d{2})/(\w{3})/(\d{4}):(\d{2}):(\d{2}):(\d{2})")
# Full ISO: 2024-01-01T10:00:00.123+08:00
_RE_ISO_FULL = re.compile(r"(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})")

_MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _parse_timestamp(ts_str: Optional[str]) -> Optional[datetime]:
    """尝试将时间戳字符串解析为 datetime 对象。

    支持 ISO 8601、Syslog、Web 日志格式。解析失败返回 None。
    """
    if not ts_str or not ts_str.strip():
        return None

    ts_str = ts_str.strip()

    # Try ISO 8601 full (with timezone stripped)
    m = _RE_ISO_FULL.match(ts_str)
    if m:
        try:
            return datetime.fromisoformat(m.group(1))
        except (ValueError, TypeError):
            pass

    # Try ISO 8601 basic
    m = _RE_ISO.match(ts_str)
    if m:
        try:
            return datetime(
                int(m.group(1)), int(m.group(2)), int(m.group(3)),
                int(m.group(4)), int(m.group(5)), int(m.group(6)),
            )
        except (ValueError, TypeError):
            pass

    # Try Web: 15/Jan/2024:10:30:00
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

    # Try Syslog: Jan 15 10:30:00
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
    """从多条日志条目构建统一时间线。

    使用 LogParseService 逐行解析，做风险研判，按时间戳排序，按实体键分组。
    """

    def __init__(self, time_window_minutes: int = 5):
        self.time_window_minutes = time_window_minutes

    async def build_timeline(
        self,
        log_lines: List[str],
        context: ContextManager,
    ) -> Tuple[List[CorrelatedEvent], Dict[str, List[CorrelatedEvent]]]:
        """从原始日志行构建时间线。

        返回:
            (sorted_timeline, entity_groups)
            - sorted_timeline: 按时间戳排序的所有事件
            - entity_groups: 按实体键分组的事件
        """
        events: List[CorrelatedEvent] = []

        for i, line in enumerate(log_lines, 1):
            line = line.strip()
            if not line:
                continue

            # 复用 LogParseService 进行解析和风险研判
            parse_result = await LogParseService.parse_log(line, context)
            if parse_result["code"] != 0:
                logger.warning(f"解析日志行 {i} 失败: {parse_result['msg']}")
                continue
            parsed = parse_result["data"]

            risk_result = await LogParseService.assess_risk(parsed, context)
            risk_data = risk_result["data"] if risk_result["code"] == 0 else {}

            event = CorrelatedEvent(
                timestamp=parsed.get("timestamp"),
                device_type=parsed.get("device_type", "unknown"),
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

        # 按时间戳排序（无时间戳事件排在最后）
        def _sort_key(e: CorrelatedEvent) -> tuple:
            dt = _parse_timestamp(e.timestamp)
            if dt is None:
                return (1, e.line_number)
            return (0, dt.timestamp(), e.line_number)

        events.sort(key=_sort_key)

        # 按实体分组
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
# ChainAnalyzer
# ---------------------------------------------------------------------------

class ChainAnalyzer:
    """分析时间线中的攻击链模式。

    从 correlation_patterns.json 加载攻击链模式，在时间线中匹配已知攻击链。
    """

    def __init__(self):
        self._patterns: List[dict] = []
        self._load_patterns()

    def _load_patterns(self):
        """从 JSON 规则文件加载攻击链模式。"""
        try:
            data = JsonConfigLoader.load(CORRELATION_PATTERNS_PATH)
            self._patterns = data.get("patterns", []) if data else []
        except (FileNotFoundError, ValueError, Exception) as e:
            logger.warning(f"加载 correlation_patterns.json 失败: {e}")
            self._patterns = []

    @property
    def patterns(self) -> List[dict]:
        return list(self._patterns)

    def analyze(
        self,
        timeline: List[CorrelatedEvent],
        entity_groups: Dict[str, List[CorrelatedEvent]],
        time_window: timedelta,
    ) -> List[AttackChain]:
        """分析时间线中的攻击链模式。

        对每个模式，扫描所有实体组以寻找匹配的事件序列。
        返回按置信度降序排列的攻击链列表。
        """
        results: List[AttackChain] = []

        if not self._patterns or not timeline:
            return results

        for pattern in self._patterns:
            stages = pattern.get("stages", [])
            if not stages:
                continue

            min_events = pattern.get("min_events", 2)
            max_window = timedelta(minutes=pattern.get("max_time_window_minutes", 10))

            # 对每个实体组进行分析
            for entity_key, group_events in entity_groups.items():
                chain = self._match_pattern_in_group(
                    pattern=pattern,
                    stages=stages,
                    events=group_events,
                    time_window=max_window,
                    entity_key=entity_key,
                )
                if chain is not None and len(chain.matched_events) >= min_events:
                    results.append(chain)

        # 按置信度降序排序
        results.sort(key=lambda c: c.confidence, reverse=True)

        # 去重：相同 chain_id + entity_key 保留最高置信度
        seen: set = set()
        deduped: List[AttackChain] = []
        for chain in results:
            dedup_key = (chain.chain_id, chain.entity_key)
            if dedup_key not in seen:
                seen.add(dedup_key)
                deduped.append(chain)

        return deduped

    def _match_pattern_in_group(
        self,
        pattern: dict,
        stages: List[dict],
        events: List[CorrelatedEvent],
        time_window: timedelta,
        entity_key: str,
    ) -> Optional[AttackChain]:
        """尝试在事件组中匹配模式的各个阶段。"""
        matched_events: List[CorrelatedEvent] = []
        matched_stages: List[str] = []
        start_time: Optional[datetime] = None

        for stage_idx, stage in enumerate(stages):
            stage_matches = []

            for event in events:
                if event in matched_events:
                    continue

                # 检查时间窗口
                if start_time is not None:
                    evt_time = _parse_timestamp(event.timestamp)
                    if evt_time and (evt_time - start_time) > time_window:
                        continue

                if self._event_matches_stage(event, stage):
                    stage_matches.append(event)

            min_count = stage.get("min_count", 1)
            if len(stage_matches) >= min_count:
                matched_events.extend(stage_matches)
                matched_stages.append(stage.get("label", f"Stage {stage_idx + 1}"))

                # 从第一个匹配事件设置开始时间
                if start_time is None and stage_matches:
                    first_ts = _parse_timestamp(stage_matches[0].timestamp)
                    if first_ts:
                        start_time = first_ts

        if not matched_events:
            return None

        # 根据匹配的阶段数计算置信度
        total_stages = len(stages)
        matched_count = len(matched_stages)
        confidence = matched_count / total_stages if total_stages > 0 else 0.0

        # 提取指标
        indicators = []
        for evt in matched_events:
            if evt.risk_desc:
                indicators.append(evt.risk_desc)
            if evt.src_ip and evt.src_ip not in indicators:
                indicators.append(f"源IP: {evt.src_ip}")
            if evt.user:
                indicators.append(f"用户: {evt.user}")

        # 去重指标
        seen_indicators: set = set()
        unique_indicators: List[str] = []
        for ind in indicators:
            if ind not in seen_indicators:
                seen_indicators.add(ind)
                unique_indicators.append(ind)

        chain = AttackChain(
            chain_id=pattern.get("id", "CHAIN-UNKNOWN"),
            chain_name=pattern.get("name", "未知攻击链"),
            description=pattern.get("description", ""),
            risk_level=pattern.get("risk_level", "P3_低风险"),
            confidence=confidence,
            matched_events=matched_events,
            matched_stages=matched_stages,
            indicators=unique_indicators[:10],
            suggestion=pattern.get("suggestion", ""),
            entity_key=entity_key,
        )

        return chain

    @staticmethod
    def _event_matches_stage(event: CorrelatedEvent, stage: dict) -> bool:
        """检查单个事件是否匹配单个阶段定义。"""
        # 设备类型检查
        dt = stage.get("device_type")
        if dt and event.device_type != dt:
            return False

        # 状态精确匹配
        status = stage.get("status")
        if status and event.matches_status(status):
            pass
        elif status:
            status_prefix = stage.get("status_startswith")
            if not status_prefix or not event.matches_status_prefix(status_prefix):
                return False

        # 状态前缀匹配
        status_prefix = stage.get("status_startswith")
        if not status and status_prefix and not event.matches_status_prefix(status_prefix):
            return False

        # 命令内容检查
        command_contains = stage.get("command_contains")
        if command_contains and not event.matches_command(command_contains):
            return False

        # 非工作时间检查
        is_off_hours = stage.get("is_off_hours", False)
        if is_off_hours:
            dt = _parse_timestamp(event.timestamp)
            if dt is None or 8 <= dt.hour <= 18:
                return False

        # 额外攻击类型匹配
        attack_type = stage.get("attack_type")
        if attack_type:
            extra_attack = event.extra_info.get("attack_type", "")
            if attack_type.lower() not in extra_attack.lower():
                return False

        return True


# ---------------------------------------------------------------------------
# LogCorrelateService — 高层 API
# ---------------------------------------------------------------------------

class LogCorrelateService:
    """日志联合审查高层服务。

    提供统一入口：
    1. 解析所有日志行
    2. 构建统一时间线
    3. 分析攻击链模式
    4. 返回结构化结果
    """

    # 类级别实例（复用，避免重复加载模式）
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
        """分析多条日志进行关联检测。

        Args:
            log_lines: 原始日志行列表。
            context: 请求上下文。
            time_window_minutes: 关联时间窗口（分钟）。
            detailed: 是否返回详细时间线。

        Returns:
            dict with keys:
              - total_events: 已解析事件总数
              - device_types: 发现的设备类型集合
              - entities: 唯一实体键列表
              - chains: 检测到的攻击链列表
              - summary: 人类可读的摘要
        """
        if not log_lines:
            return Result.ok({
                "total_events": 0,
                "device_types": [],
                "entities": [],
                "chains": [],
                "summary": "没有日志可供分析",
            })

        # 构建时间线
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

        # 分析攻击链
        analyzer = cls._get_analyzer()
        chains = analyzer.analyze(timeline, entity_groups, time_window)

        # 收集统计信息
        device_types = sorted(set(e.device_type for e in timeline if e.device_type != "unknown"))
        entities = sorted(set(e.get_entity_key() for e in timeline))

        # 构建摘要
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
                "id": p.get("id"),
                "name": p.get("name"),
                "risk_level": p.get("risk_level"),
                "stages": [s.get("label") for s in p.get("stages", [])],
            }
            for p in analyzer.patterns
        ]