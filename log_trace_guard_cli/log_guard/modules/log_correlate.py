"""
Module 6: Log Correlation — Joint Log Analysis across Multiple Sources

Provides cross-source log correlation infrastructure:
  - TimelineBuilder: parse and sort logs from multiple sources by time
  - ChainAnalyzer: detect attack chain patterns from correlated timeline
  - LogCorrelateService: high-level API for joint log review

Reuses existing LogParseService for single-log parsing and risk assessment.
"""
import json
import logging
import re
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from log_guard.common.utils import JsonConfigLoader, LogManager, Result
from log_guard.modules.log_parse import LogParseService

logger = LogManager.get_logger("log_correlate")


# ---------------------------------------------------------------------------
# CorrelatedEvent — Single event on the timeline
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
        """Check if event matches a device type (exact match)."""
        return self.device_type == device_type

    def matches_status(self, status: str) -> bool:
        """Check if event status matches exactly."""
        return self.status == status

    def matches_status_prefix(self, prefixes: List[str]) -> bool:
        """Check if event status starts with any of the given prefixes."""
        if not self.status:
            return False
        return any(self.status.startswith(p) for p in prefixes)

    def matches_command(self, keywords: List[str]) -> bool:
        """Check if event command contains any of the keywords."""
        if not self.command:
            return False
        cmd_lower = self.command.lower()
        return any(kw.lower() in cmd_lower for kw in keywords)

    def get_entity_key(self) -> str:
        """Get the primary entity key (src_ip > user > device) for grouping."""
        if self.src_ip:
            return self.src_ip
        if self.user:
            return self.user
        return self.device_type


# ---------------------------------------------------------------------------
# AttackChain — Detected attack chain result
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
# Timestamp parsing helpers
# ---------------------------------------------------------------------------

# ISO 8601: 2024-01-01T10:00:00 or 2024-01-01 10:00:00
_RE_ISO = re.compile(
    r"(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})"
)
# Syslog: Jan 15 10:30:00
_RE_SYSLOG = re.compile(
    r"(\w{3})\s+(\d{1,2})\s+(\d{2}):(\d{2}):(\d{2})"
)
# Web: 15/Jan/2024:10:30:00
_RE_WEB = re.compile(
    r"(\d{2})/(\w{3})/(\d{4}):(\d{2}):(\d{2}):(\d{2})"
)
# Full: 2024-01-01T10:00:00.123+08:00
_RE_ISO_FULL = re.compile(
    r"(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})"
)

_MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _parse_timestamp(ts_str: Optional[str]) -> Optional[datetime]:
    """Try to parse a timestamp string into a datetime object.

    Supports ISO 8601, Syslog, and Web log formats.
    Returns None if parsing fails.
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
    """Build a unified timeline from multiple log entries.

    Parses each log line using LogParseService, runs risk assessment,
    sorts by timestamp, and groups by entity key (IP > user > device).
    """

    def __init__(self, time_window_minutes: int = 5):
        self._parse_svc = LogParseService()
        self.time_window_minutes = time_window_minutes

    def build_timeline(
        self,
        log_lines: List[str],
        source_label: str = "input",
    ) -> Tuple[List[CorrelatedEvent], Dict[str, List[CorrelatedEvent]]]:
        """Build a timeline from raw log lines.

        Returns:
            (sorted_timeline, entity_groups)
            - sorted_timeline: all events sorted by timestamp
            - entity_groups: events grouped by entity key (src_ip > user > device)
        """
        events: List[CorrelatedEvent] = []

        for i, line in enumerate(log_lines, 1):
            line = line.strip()
            if not line:
                continue

            # Reuse LogParseService for parsing and risk assessment
            parsed = self._parse_svc.parse_log(line)
            risk = self._parse_svc.assess_risk(parsed)

            event = CorrelatedEvent(
                timestamp=parsed.get("timestamp"),
                device_type=parsed.get("device_type", "unknown"),
                src_ip=parsed.get("src_ip"),
                dst_ip=parsed.get("dst_ip"),
                user=parsed.get("user"),
                status=parsed.get("status"),
                command=parsed.get("command"),
                raw_log=line,
                risk_level=risk.get("risk_level", "P3_噪音"),
                risk_desc=risk.get("risk_desc", ""),
                extra_info=parsed.get("extra_info", {}),
                line_number=i,
            )
            events.append(event)

        # Sort by timestamp (events without timestamp go to end)
        def _sort_key(e: CorrelatedEvent) -> tuple:
            dt = _parse_timestamp(e.timestamp)
            if dt is None:
                return (1, e.line_number)  # Untimestamped events at end, by line number
            return (0, dt.timestamp(), e.line_number)

        events.sort(key=_sort_key)

        # Group by entity
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
    """Analyze a timeline for attack chain patterns.

    Loads patterns from correlation_patterns.json and matches them
    against the timeline to detect known attack chains.
    """

    def __init__(self):
        self._patterns: List[dict] = []
        self._load_patterns()

    def _load_patterns(self):
        """Load attack chain patterns from JSON rule file."""
        try:
            data = JsonConfigLoader.load("correlation_patterns.json")
            self._patterns = data.get("patterns", [])
        except (FileNotFoundError, ValueError, Exception) as e:
            logger.warning(f"Cannot load correlation_patterns.json: {e}")
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
        """Analyze timeline for attack chain patterns.

        For each pattern, scan all entity groups for matching event sequences.
        Returns a list of detected AttackChain objects, sorted by confidence.
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

            # Analyze per entity group
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

        # Sort by confidence descending
        results.sort(key=lambda c: c.confidence, reverse=True)

        # Deduplicate: same chain_id and same entity_key, keep highest confidence
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
        """Try to match a pattern's stages against a group of events."""
        matched_events: List[CorrelatedEvent] = []
        matched_stages: List[str] = []
        stage_counts: Dict[int, int] = {}  # stage index -> matched count
        start_time: Optional[datetime] = None

        for stage_idx, stage in enumerate(stages):
            stage_matches = []

            for event in events:
                if event in matched_events:
                    continue

                # Check time window (if we already have a start time)
                if start_time is not None:
                    evt_time = _parse_timestamp(event.timestamp)
                    if evt_time and (evt_time - start_time) > time_window:
                        continue  # This event is outside the window

                if self._event_matches_stage(event, stage):
                    stage_matches.append(event)

            min_count = stage.get("min_count", 1)
            if len(stage_matches) >= min_count:
                matched_events.extend(stage_matches)
                matched_stages.append(stage.get("label", f"Stage {stage_idx + 1}"))
                stage_counts[stage_idx] = len(stage_matches)

                # Set start time from first matched event
                if start_time is None and stage_matches:
                    first_ts = _parse_timestamp(stage_matches[0].timestamp)
                    if first_ts:
                        start_time = first_ts

        if not matched_events:
            return None

        # Calculate confidence based on stages matched
        total_stages = len(stages)
        matched_count = len(matched_stages)
        confidence = matched_count / total_stages if total_stages > 0 else 0.0

        # Extract indicators from matched events
        indicators = []
        for evt in matched_events:
            if evt.risk_desc:
                indicators.append(evt.risk_desc)
            if evt.src_ip and evt.src_ip not in indicators:
                indicators.append(f"源IP: {evt.src_ip}")
            if evt.user:
                indicators.append(f"用户: {evt.user}")

        # Deduplicate indicators
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
        """Check if a single event matches a single stage definition."""
        # Device type check
        dt = stage.get("device_type")
        if dt and event.device_type != dt:
            return False

        # Status exact match
        status = stage.get("status")
        if status and event.matches_status(status):
            pass  # Status matched
        elif status:
            # Status specified but doesn't match
            # But check status_prefix as fallback
            status_prefix = stage.get("status_startswith")
            if not status_prefix or not event.matches_status_prefix(status_prefix):
                return False

        # Status prefix match (used when no exact status match)
        status_prefix = stage.get("status_startswith")
        if not status and status_prefix and not event.matches_status_prefix(status_prefix):
            return False

        # Command content check
        command_contains = stage.get("command_contains")
        if command_contains and not event.matches_command(command_contains):
            return False

        # Off-hours check (hour < 8 or hour > 18)
        is_off_hours = stage.get("is_off_hours", False)
        if is_off_hours:
            dt = _parse_timestamp(event.timestamp)
            if dt is None or 8 <= dt.hour <= 18:
                return False

        # Extra info attack_type match
        attack_type = stage.get("attack_type")
        if attack_type:
            extra_attack = event.extra_info.get("attack_type", "")
            if attack_type.lower() not in extra_attack.lower():
                return False

        return True


# ---------------------------------------------------------------------------
# LogCorrelateService — High-level API
# ---------------------------------------------------------------------------

class LogCorrelateService:
    """High-level service for joint log correlation analysis.

    Provides a single entry point that:
    1. Parses all log lines
    2. Builds a unified timeline
    3. Analyzes attack chain patterns
    4. Returns structured results
    """

    def __init__(self):
        self._timeline_builder = TimelineBuilder()
        self._chain_analyzer = ChainAnalyzer()

    def correlate_logs(
        self,
        log_lines: List[str],
        time_window_minutes: int = 5,
        detailed: bool = False,
    ) -> Dict[str, Any]:
        """Analyze multiple log lines for correlation.

        Args:
            log_lines: List of raw log line strings.
            time_window_minutes: Time window for event correlation.
            detailed: If True, include full event details.

        Returns:
            dict with keys:
              - total_events: total parsed event count
              - device_types: set of device types found
              - entities: unique entity keys found
              - timeline: sorted timeline (detailed only)
              - chains: list of detected attack chains
              - summary: human-readable summary
        """
        if not log_lines:
            return Result.ok({
                "total_events": 0,
                "device_types": [],
                "entities": [],
                "timeline": [],
                "chains": [],
                "summary": "没有日志可供分析",
            })

        # Update time window
        self._timeline_builder.time_window_minutes = time_window_minutes
        time_window = self._timeline_builder.get_time_window()

        # Build timeline
        timeline, entity_groups = self._timeline_builder.build_timeline(log_lines)

        if not timeline:
            return Result.ok({
                "total_events": 0,
                "device_types": [],
                "entities": [],
                "timeline": [],
                "chains": [],
                "summary": "未能解析任何日志行",
            })

        # Analyze chains
        chains = self._chain_analyzer.analyze(timeline, entity_groups, time_window)

        # Collect stats
        device_types = sorted(set(e.device_type for e in timeline if e.device_type != "unknown"))
        entities = sorted(set(e.get_entity_key() for e in timeline))

        # Build summary
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

    def correlate_logs_from_file(
        self,
        file_path: str,
        line_limit: int = 500,
        grep: Optional[str] = None,
        time_window_minutes: int = 5,
        detailed: bool = False,
    ) -> Dict[str, Any]:
        """Analyze logs from a file for correlation.

        Args:
            file_path: Path to log file.
            line_limit: Max lines to read.
            grep: Optional keyword filter.
            time_window_minutes: Time window for correlation.
            detailed: Include full event details.

        Returns:
            Same structure as correlate_logs().
        """
        from log_guard.core.log_reader import LogReader

        reader = LogReader()
        result = reader.read_log(file_path, line_limit=line_limit, grep=grep)
        lines = result.get("lines", [])

        if not lines:
            return Result.ok({
                "total_events": 0,
                "device_types": [],
                "entities": [],
                "timeline": [],
                "chains": [],
                "summary": f"文件 {file_path} 中没有匹配的日志行",
                "source_file": file_path,
            })

        correlation = self.correlate_logs(lines, time_window_minutes, detailed)
        if isinstance(correlation, dict):
            correlation["source_file"] = file_path
            correlation["file_total_lines"] = result.get("total_lines", 0)
        return correlation

    @property
    def available_patterns(self) -> List[dict]:
        """Return list of available attack chain patterns (for display)."""
        return [
            {
                "id": p.get("id"),
                "name": p.get("name"),
                "risk_level": p.get("risk_level"),
                "stages": [s.get("label") for s in p.get("stages", [])],
            }
            for p in self._chain_analyzer.patterns
        ]