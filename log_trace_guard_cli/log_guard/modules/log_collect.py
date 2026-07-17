"""
Module 2: Log Collection + Fault Diagnosis

Provides log collection planning, device matching, strategy-based plan
generation, fault diagnosis, and architecture recommendation.

Supports dynamic registration of collection strategies and uses the
project's JSON config loader for device_protocol.json, collect_templates.json,
fault_kb.json, and arch_templates.json.
"""

import logging
import re
import threading
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Set, Tuple, Type

from log_guard.common.utils import JsonConfigLoader, LogManager, Result

logger = LogManager.get_logger("log_collect")


# ---------------------------------------------------------------------------
# CollectPlan
# ---------------------------------------------------------------------------

@dataclass
class CollectPlan:
    """A complete log collection plan for a specific device."""

    device_type: str = ""
    device_model: str = ""
    protocol: str = ""
    architecture: str = "small"
    steps: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    config_template: Optional[str] = None
    rag_supplements: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict, excluding None values."""
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}

    def to_dict_all(self) -> Dict[str, Any]:
        """Convert to dict including all fields."""
        return asdict(self)


# ---------------------------------------------------------------------------
# FaultDiagnosis
# ---------------------------------------------------------------------------

@dataclass
class FaultDiagnosis:
    """Structured diagnosis result for a single fault type."""

    fault_type: str = ""
    fault_desc: str = ""
    severity: str = "medium"
    match_score: float = 0.0
    possible_causes: List[str] = field(default_factory=list)
    fix_steps: List[str] = field(default_factory=list)
    prevention: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Strategy base class
# ---------------------------------------------------------------------------

class BaseCollectStrategy:
    """Abstract base for collection strategy implementations."""

    name: str = "base"

    def get_plan(self, device_type: str, device_model: str,
                 scale: str) -> Optional[CollectPlan]:
        """
        Return a CollectPlan for the given device, or None if this
        strategy cannot handle the request.
        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Built-in strategies
# ---------------------------------------------------------------------------

class DeviceProtocolStrategy(BaseCollectStrategy):
    """
    Strategy that uses device_protocol.json for device metadata and
    collect_templates.json for protocol-specific step templates.
    """

    name = "device_protocol"

    def get_plan(self, device_type: str, device_model: str,
                 scale: str) -> Optional[CollectPlan]:
        try:
            proto_data = JsonConfigLoader.load("device_protocol.json")
            templates = JsonConfigLoader.load("collect_templates.json")
        except (FileNotFoundError, ValueError, Exception) as e:
            logger.debug(f"Could not load config data: {e}")
            return None

        entries = proto_data.get("entries", {})
        if device_model not in entries:
            # Try device_type as fallback
            model_key = device_type
        else:
            model_key = device_model

        entry = entries.get(model_key)
        if entry is None:
            return None

        protocol = entry.get("protocol", "syslog")
        device_type_from_entry = entry.get("type", device_type)
        vendor = entry.get("vendor", "")

        # Resolve scale
        resolved_scale = scale if scale in ("small", "large") else "small"

        # Build plan from template
        plan = CollectPlan(
            device_type=device_type_from_entry,
            device_model=device_model or model_key,
            protocol=protocol,
            architecture=resolved_scale,
        )

        # Fill in template data
        template_data = templates.get("templates", {})
        if protocol in template_data:
            scale_data = template_data[protocol].get(resolved_scale)
            if scale_data:
                plan.steps = list(scale_data.get("steps", []))
                plan.notes = list(scale_data.get("notes", []))
                # Build config template hint
                cfg_parts = []
                if "port" in scale_data:
                    cfg_parts.append(f"port={scale_data['port']}")
                if "transport" in scale_data:
                    cfg_parts.append(f"transport={scale_data['transport']}")
                if "collector" in scale_data:
                    cfg_parts.append(f"collector={scale_data['collector']}")
                if "format" in scale_data:
                    cfg_parts.append(f"format={scale_data['format']}")
                if cfg_parts:
                    plan.config_template = f"{protocol}://{vendor}/{device_model}?" + "&".join(cfg_parts)
                # RAG supplements
                if "log_hints" in entry:
                    plan.rag_supplements = list(entry["log_hints"])
                if "server_config" in scale_data:
                    plan.rag_supplements.append(f"config_file: {scale_data['server_config']}")
        else:
            # Fallback: generic steps
            plan.steps = [
                f"1. 确认 {vendor} {device_model} 设备状态",
                f"2. 配置 {protocol} 日志采集协议",
                f"3. 部署采集代理并连接目标设备",
                f"4. 配置日志解析规则",
                "5. 验证日志采集完整性",
            ]
            plan.notes = [f"设备 {device_model} 使用 {protocol} 协议采集"]

        return plan


class DefaultFallbackStrategy(BaseCollectStrategy):
    """
    Fallback strategy that returns a minimal plan for any device type.
    """

    name = "default_fallback"

    def get_plan(self, device_type: str, device_model: str,
                 scale: str) -> Optional[CollectPlan]:
        resolved_scale = scale if scale in ("small", "large") else "small"
        plan = CollectPlan(
            device_type=device_type,
            device_model=device_model or device_type,
            protocol="syslog",
            architecture=resolved_scale,
            steps=[
                f"1. 确认 {device_type} 设备网络可达",
                "2. 配置 Syslog 日志推送",
                "3. 部署采集代理",
                "4. 配置日志解析规则",
                "5. 验证采集结果",
            ],
            notes=[
                f"使用默认 Syslog 协议采集 {device_type} 日志",
                "建议查阅设备文档确认具体配置方法",
            ],
            config_template=f"syslog://{device_model}:514",
            rag_supplements=[f"device_type={device_type}", f"model={device_model}"],
        )
        return plan


# ---------------------------------------------------------------------------
# CollectStrategyFactory
# ---------------------------------------------------------------------------

class CollectStrategyFactory:
    """
    Factory for collecting strategies.

    Maintains a registry of strategy classes and selects the best
    strategy for a given device type/model.
    """

    def __init__(self):
        self._strategies: Dict[str, Type[BaseCollectStrategy]] = {}
        self._instances: Dict[str, BaseCollectStrategy] = {}

    def register(self, name: str, strategy_class: Type[BaseCollectStrategy]) -> None:
        """Register a strategy class with a given name."""
        self._strategies[name] = strategy_class

    def get_plan(self, device_type: str, device_model: str,
                 scale: str) -> Optional[CollectPlan]:
        """
        Iterate through registered strategies and return the first
        non-None CollectPlan.
        """
        for name in self._strategies:
            strategy = self._get_or_create(name)
            try:
                plan = strategy.get_plan(device_type, device_model, scale)
                if plan is not None:
                    return plan
            except Exception as e:
                logger.debug(f"Strategy '{name}' failed: {e}")
                continue
        return None

    def _get_or_create(self, name: str) -> BaseCollectStrategy:
        if name not in self._instances:
            self._instances[name] = self._strategies[name]()
        return self._instances[name]

    @property
    def registered_strategies(self) -> List[str]:
        return list(self._strategies.keys())


# Default strategy registration
_default_strategy_factory: Optional[CollectStrategyFactory] = None


def _register_default_strategies() -> CollectStrategyFactory:
    factory = CollectStrategyFactory()
    factory.register("device_protocol", DeviceProtocolStrategy)
    factory.register("default_fallback", DefaultFallbackStrategy)
    return factory


def get_default_strategy_factory() -> CollectStrategyFactory:
    global _default_strategy_factory
    if _default_strategy_factory is None:
        _default_strategy_factory = _register_default_strategies()
    return _default_strategy_factory


_default_strategy_factory = _register_default_strategies()


# ---------------------------------------------------------------------------
# DeviceMatcher
# ---------------------------------------------------------------------------

class DeviceMatcher:
    """
    Matches device requests to known device types from the device_protocol
    knowledge base.

    Provides confidence scores, device info, and match source metadata.
    """

    def __init__(self):
        self._device_protocol_cache: Optional[Dict[str, Any]] = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # get_recommendation
    # ------------------------------------------------------------------

    def get_recommendation(self, device_type: str, device_model: str,
                           scale: str) -> Dict[str, Any]:
        """
        Return a recommendation dict for the given device.

        Returns:
            dict with keys:
              - plan: CollectPlan (or None)
              - match_confidence: float 0~1
              - device_info: dict with device metadata
              - match_source: str describing how the match was made
        """
        default = {
            "plan": None,
            "match_confidence": 0.0,
            "device_info": {},
            "match_source": "no_match",
        }

        try:
            proto_data = self._load_protocol_data()
        except Exception as e:
            logger.warning(f"Could not load device_protocol.json: {e}")
            return default

        entries = proto_data.get("entries", {})
        factory = get_default_strategy_factory()

        # Try exact model match first
        if device_model and device_model in entries:
            entry = entries[device_model]
            plan = factory.get_plan(device_type, device_model, scale)
            if plan is None:
                plan = factory.get_plan(device_type, device_model, scale)
            return {
                "plan": plan,
                "match_confidence": 0.95,
                "device_info": {
                    "type": entry.get("type", device_type),
                    "vendor": entry.get("vendor", ""),
                    "protocol": entry.get("protocol", "syslog"),
                    "log_hints": entry.get("log_hints", []),
                },
                "match_source": f"exact_model_match:{device_model}",
            }

        # Try device_type fallback
        type_candidates = {
            k: v for k, v in entries.items()
            if v.get("type", "").lower() == device_type.lower()
        }
        if type_candidates:
            best_key = next(iter(type_candidates))
            entry = type_candidates[best_key]
            plan = factory.get_plan(device_type, device_model, scale)
            return {
                "plan": plan,
                "match_confidence": 0.70,
                "device_info": {
                    "type": entry.get("type", device_type),
                    "vendor": entry.get("vendor", ""),
                    "protocol": entry.get("protocol", "syslog"),
                    "log_hints": entry.get("log_hints", []),
                },
                "match_source": f"type_match:{device_type}->{best_key}",
            }

        # Fuzzy fallback: try substring matching
        if device_model:
            for key, entry in entries.items():
                if device_model.lower() in key.lower() or key.lower() in device_model.lower():
                    plan = factory.get_plan(device_type, device_model, scale)
                    return {
                        "plan": plan,
                        "match_confidence": 0.50,
                        "device_info": {
                            "type": entry.get("type", device_type),
                            "vendor": entry.get("vendor", ""),
                            "protocol": entry.get("protocol", "syslog"),
                            "log_hints": entry.get("log_hints", []),
                        },
                        "match_source": f"fuzzy_model_match:{key}",
                    }

        # Last resort: use fallback strategy
        plan = factory.get_plan(device_type, device_model, scale)
        return {
            "plan": plan,
            "match_confidence": 0.35,
            "device_info": {
                "type": device_type,
                "vendor": "unknown",
                "protocol": "syslog",
                "log_hints": [],
            },
            "match_source": "fallback_strategy",
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_protocol_data(self) -> Dict[str, Any]:
        """Load and cache device_protocol.json."""
        with self._lock:
            if self._device_protocol_cache is None:
                self._device_protocol_cache = JsonConfigLoader.load("device_protocol.json")
            return self._device_protocol_cache

    def reload_protocol_data(self) -> None:
        """Force reload device_protocol.json from disk."""
        with self._lock:
            self._device_protocol_cache = JsonConfigLoader.reload("device_protocol.json")


# ---------------------------------------------------------------------------
# FaultFixer
# ---------------------------------------------------------------------------

class FaultFixer:
    """
    Fault diagnosis engine that uses fault_kb.json as its knowledge base.

    Supports:
      - Token-based keyword extraction and fuzzy matching
      - Multi-field diagnosis (symptom, protocol, device_type, error_log)
      - Cached knowledge base with hot-reload
    """

    def __init__(self):
        self._kb_cache: Optional[Dict[str, Any]] = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # diagnose
    # ------------------------------------------------------------------

    def diagnose(self, symptom: str = "",
                 protocol: str = "",
                 device_type: str = "",
                 error_log: str = "") -> Tuple[Optional[FaultDiagnosis], List[Dict[str, Any]]]:
        """
        Diagnose a fault based on the provided evidence.

        Args:
            symptom: User-described symptom text.
            protocol: Protocol hint (e.g., "ssh", "syslog", "tcp").
            device_type: Device type hint (e.g., "firewall", "server").
            error_log: Raw error log text.

        Returns:
            Tuple of (best_diagnosis, candidates) where:
              best_diagnosis: FaultDiagnosis with highest match score, or None.
              candidates: List of candidate diagnosis dicts sorted by score desc.
        """
        try:
            kb = self._load_kb()
        except Exception as e:
            logger.warning(f"Could not load fault_kb.json: {e}")
            return None, []

        entries = kb.get("entries", {})
        if not entries:
            return None, []

        # Build search text
        search_parts = []
        if symptom:
            search_parts.append(symptom)
        if error_log:
            search_parts.append(error_log)
        if protocol:
            search_parts.append(protocol)
        if device_type:
            search_parts.append(device_type)
        search_text = " ".join(search_parts)

        if not search_text.strip():
            return None, []

        search_tokens = self._extract_tokens(search_text)

        # Score each entry
        scored: List[Tuple[float, str, List[str]]] = []
        for fault_key, fault_data in entries.items():
            score, matched_keywords = self._calculate_match_score(
                search_text, search_tokens, fault_data
            )
            if score > 0:
                scored.append((score, fault_key, matched_keywords))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)

        candidates = []
        best_diagnosis = None

        for score, fault_key, matched_keywords in scored:
            fault_data = entries[fault_key]
            diagnosis = FaultDiagnosis(
                fault_type=fault_data.get("fault_type", fault_key),
                fault_desc=fault_data.get("fault_desc", ""),
                severity=fault_data.get("severity", "medium"),
                match_score=round(score, 4),
                possible_causes=list(fault_data.get("possible_causes", [])),
                fix_steps=list(fault_data.get("fix_steps", [])),
                prevention=list(fault_data.get("prevention", [])),
            )

            candidate = diagnosis.to_dict()
            candidate["fault_key"] = fault_key
            candidate["matched_keywords"] = matched_keywords
            candidates.append(candidate)

            if best_diagnosis is None:
                best_diagnosis = diagnosis

        return best_diagnosis, candidates

    # ------------------------------------------------------------------
    # get_all_faults
    # ------------------------------------------------------------------

    def get_all_faults(self) -> List[Dict[str, Any]]:
        """Return a list of all known fault types with basic info."""
        try:
            kb = self._load_kb()
        except Exception as e:
            logger.warning(f"Could not load fault_kb.json: {e}")
            return []

        entries = kb.get("entries", {})
        results = []
        for fault_key, fault_data in entries.items():
            results.append({
                "fault_key": fault_key,
                "fault_type": fault_data.get("fault_type", ""),
                "fault_desc": fault_data.get("fault_desc", ""),
                "severity": fault_data.get("severity", "medium"),
            })
        return results

    # ------------------------------------------------------------------
    # get_fault_detail
    # ------------------------------------------------------------------

    def get_fault_detail(self, fault_type: str) -> Optional[Dict[str, Any]]:
        """
        Return detailed diagnosis data for a specific fault type.

        Args:
            fault_type: The fault key or fault_type name to look up.

        Returns:
            dict with full diagnosis data, or None if not found.
        """
        try:
            kb = self._load_kb()
        except Exception as e:
            logger.warning(f"Could not load fault_kb.json: {e}")
            return None

        entries = kb.get("entries", {})

        # Try exact fault_key match first
        if fault_type in entries:
            return dict(entries[fault_type])

        # Try matching by fault_type field
        for fault_key, fault_data in entries.items():
            if fault_data.get("fault_type", "") == fault_type:
                result = dict(fault_data)
                result["fault_key"] = fault_key
                return result

        # Try fuzzy match
        ft_lower = fault_type.lower()
        for fault_key, fault_data in entries.items():
            if ft_lower in fault_key.lower() or ft_lower in fault_data.get("fault_type", "").lower():
                result = dict(fault_data)
                result["fault_key"] = fault_key
                return result

        return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_kb(self) -> Dict[str, Any]:
        """Load and cache fault_kb.json."""
        with self._lock:
            if self._kb_cache is None:
                self._kb_cache = JsonConfigLoader.load("fault_kb.json")
            return self._kb_cache

    def reload_kb(self) -> None:
        """Force reload fault_kb.json from disk, updating the cache."""
        with self._lock:
            self._kb_cache = JsonConfigLoader.reload("fault_kb.json")

    @staticmethod
    def _extract_tokens(text: str) -> Set[str]:
        """
        Extract meaningful tokens from text.

        Splits on whitespace and punctuation, filters out short tokens
        and common stop words.
        """
        stop_words = {
            "的", "了", "是", "在", "不", "有", "和", "就", "也", "都",
            "而", "及", "与", "着", "或", "一个", "没有", "我们", "你们",
            "他们", "这个", "那个", "什么", "怎么", "如何", "a", "an",
            "the", "is", "it", "to", "in", "for", "of", "on", "and",
            "or", "that", "this", "with", "from", "by", "at", "be",
            "are", "was", "were", "been", "being", "have", "has", "had",
            "do", "does", "did", "will", "would", "can", "could",
            "not", "no", "but", "if", "so", "as",
        }
        tokens = set()
        for part in re.split(r"[\s,;:!?，。；：！？、()（）\[\]【】/\\\"'{}]", text):
            part = part.strip().lower()
            if len(part) >= 2 and part not in stop_words:
                tokens.add(part)
        return tokens

    @staticmethod
    def _fuzzy_match_keyword(keyword: str, text: str) -> float:
        """
        Compute a fuzzy match score between a keyword and text.

        Returns a float 0~1:
          - 1.0: exact match
          - 0.8: keyword is a substring of text or vice versa
          - 0.5: partial overlap (e.g., shared words)
          - 0.0: no match
        """
        kw_lower = keyword.lower().strip()
        text_lower = text.lower().strip()

        if not kw_lower or not text_lower:
            return 0.0

        # Exact match
        if kw_lower == text_lower:
            return 1.0

        # Substring
        if kw_lower in text_lower or text_lower in kw_lower:
            return 0.8

        # Token overlap
        kw_tokens = set(kw_lower.split())
        text_tokens = set(text_lower.split())
        if not kw_tokens or not text_tokens:
            return 0.0

        intersection = kw_tokens & text_tokens
        if intersection:
            return min(len(intersection) / len(kw_tokens), 0.5)

        return 0.0

    @staticmethod
    def _calculate_match_score(search_text: str, search_tokens: Set[str],
                                fault_data: Dict[str, Any]) -> Tuple[float, List[str]]:
        """
        Calculate how well a fault entry matches the search text/tokens.

        Scoring factors:
          - Keyword matches (primary)
          - Protocol hints (secondary)
          - Token overlap (tertiary)

        Returns:
            Tuple of (score, matched_keywords).
        """
        score = 0.0
        matched_keywords: List[str] = []

        # Factor 1: Keyword matches
        keywords = fault_data.get("keywords", [])
        for kw in keywords:
            match_score = FaultFixer._fuzzy_match_keyword(kw, search_text)
            if match_score > 0:
                score += match_score * 0.6  # Keyword weight
                if kw not in matched_keywords:
                    matched_keywords.append(kw)

        # Factor 2: Protocol hints
        protocol_hints = fault_data.get("protocol_hints", [])
        for hint in protocol_hints:
            hint_lower = hint.lower()
            if hint_lower in search_text.lower():
                score += 0.3
                if hint not in matched_keywords:
                    matched_keywords.append(f"protocol:{hint}")

        # Factor 3: Token overlap
        fault_text = " ".join([
            fault_data.get("fault_type", ""),
            fault_data.get("fault_desc", ""),
            " ".join(fault_data.get("keywords", [])),
        ])
        fault_tokens = FaultFixer._extract_tokens(fault_text)
        if search_tokens and fault_tokens:
            overlap = search_tokens & fault_tokens
            token_score = len(overlap) / max(len(search_tokens), 1)
            score += token_score * 0.1

        # Factor 4: fault_type / fault_desc exact match boost
        ft = fault_data.get("fault_type", "")
        fd = fault_data.get("fault_desc", "")
        if ft and ft in search_text:
            score += 0.5
        if fd and fd in search_text:
            score += 0.3

        return round(score, 4), matched_keywords


# ---------------------------------------------------------------------------
# LogCollectService
# ---------------------------------------------------------------------------

class LogCollectService:
    """
    High-level service for log collection planning, fault diagnosis,
    and architecture recommendation.

    Wraps DeviceMatcher, CollectStrategyFactory, and FaultFixer with
    a unified Result-based API.
    """

    def __init__(self, matcher: Optional[DeviceMatcher] = None,
                 strategy_factory: Optional[CollectStrategyFactory] = None,
                 fault_fixer: Optional[FaultFixer] = None):
        self.matcher = matcher or DeviceMatcher()
        self.strategy_factory = strategy_factory or get_default_strategy_factory()
        self.fault_fixer = fault_fixer or FaultFixer()

    # ------------------------------------------------------------------
    # match_device
    # ------------------------------------------------------------------

    def match_device(self, device_type: str, device_model: str,
                     scale: str = "small") -> dict:
        """
        Match a device against the knowledge base and return a recommendation.

        Args:
            device_type: Device type (e.g., "firewall", "server", "db", "web", "waf").
            device_model: Device model (e.g., "paloalto", "fortigate", "linux").
            scale: Deployment scale ("small" or "large", default "small").

        Returns:
            Result dict with the recommendation data.
        """
        try:
            recommendation = self.matcher.get_recommendation(device_type, device_model, scale)
            return Result.ok(data={
                "device_type": device_type,
                "device_model": device_model,
                "scale": scale,
                "plan": recommendation["plan"].to_dict() if recommendation["plan"] else None,
                "match_confidence": recommendation["match_confidence"],
                "device_info": recommendation["device_info"],
                "match_source": recommendation["match_source"],
            })
        except Exception as e:
            logger.error(f"match_device failed: {e}", exc_info=True)
            return Result.fail(f"Device matching failed: {e}", code=500)

    # ------------------------------------------------------------------
    # generate_plan
    # ------------------------------------------------------------------

    def generate_plan(self, device_type: str, device_model: str,
                      scale: str = "small",
                      include_config: bool = True) -> dict:
        """
        Generate a collection plan for a device.

        Args:
            device_type: Device type.
            device_model: Device model.
            scale: "small" or "large".
            include_config: If True, include config_template in the response.

        Returns:
            Result dict with the plan data.
        """
        try:
            plan = self.strategy_factory.get_plan(device_type, device_model, scale)
            if plan is None:
                return Result.fail(
                    f"No plan available for device_type={device_type}, model={device_model}",
                    code=404,
                )

            plan_data = plan.to_dict()
            if not include_config:
                plan_data.pop("config_template", None)

            return Result.ok(data={
                "device_type": device_type,
                "device_model": device_model,
                "scale": scale,
                "plan": plan_data,
            })
        except Exception as e:
            logger.error(f"generate_plan failed: {e}", exc_info=True)
            return Result.fail(f"Plan generation failed: {e}", code=500)

    # ------------------------------------------------------------------
    # batch_generate_plans
    # ------------------------------------------------------------------

    def batch_generate_plans(self, devices: List[Dict[str, Any]]) -> dict:
        """
        Generate collection plans for multiple devices.

        Args:
            devices: List of dicts, each with keys:
                - device_type (str, required)
                - device_model (str, optional)
                - scale (str, optional, default "small")
                - include_config (bool, optional, default True)

        Returns:
            Result dict with a list of plan results.
        """
        if not devices:
            return Result.fail("No devices provided", code=400)

        results = []
        success_count = 0
        fail_count = 0

        for idx, device in enumerate(devices):
            device_type = device.get("device_type", "")
            device_model = device.get("device_model", "")
            scale = device.get("scale", "small")
            include_config = device.get("include_config", True)

            if not device_type:
                fail_count += 1
                results.append({
                    "index": idx,
                    "device_type": device_type,
                    "device_model": device_model,
                    "error": "Missing device_type",
                    "success": False,
                })
                continue

            try:
                plan = self.strategy_factory.get_plan(device_type, device_model, scale)
                if plan is None:
                    fail_count += 1
                    results.append({
                        "index": idx,
                        "device_type": device_type,
                        "device_model": device_model,
                        "error": f"No plan available",
                        "success": False,
                    })
                else:
                    plan_data = plan.to_dict()
                    if not include_config:
                        plan_data.pop("config_template", None)
                    success_count += 1
                    results.append({
                        "index": idx,
                        "device_type": device_type,
                        "device_model": device_model,
                        "plan": plan_data,
                        "success": True,
                    })
            except Exception as e:
                fail_count += 1
                results.append({
                    "index": idx,
                    "device_type": device_type,
                    "device_model": device_model,
                    "error": str(e),
                    "success": False,
                })

        return Result.ok(data={
            "total": len(devices),
            "success_count": success_count,
            "fail_count": fail_count,
            "results": results,
        })

    # ------------------------------------------------------------------
    # diagnose_fault
    # ------------------------------------------------------------------

    def diagnose_fault(self, symptom: str = "",
                       device_type: str = "",
                       protocol: str = "",
                       error_log: str = "") -> dict:
        """
        Diagnose a fault based on symptom, device type, protocol, and error log.

        Args:
            symptom: User-described symptom text.
            device_type: Device type hint.
            protocol: Protocol hint.
            error_log: Raw error log text.

        Returns:
            Result dict with the best diagnosis and candidate list.
        """
        if not symptom and not error_log:
            return Result.fail("No symptom or error_log provided", code=400)

        try:
            best_diagnosis, candidates = self.fault_fixer.diagnose(
                symptom=symptom,
                protocol=protocol,
                device_type=device_type,
                error_log=error_log,
            )

            if best_diagnosis is None:
                return Result.fail(
                    "No matching fault found in knowledge base",
                    code=404,
                    data={"candidates": candidates},
                )

            return Result.ok(data={
                "symptom": symptom,
                "device_type": device_type,
                "protocol": protocol,
                "best_diagnosis": best_diagnosis.to_dict(),
                "candidates": candidates,
                "total_candidates": len(candidates),
            })
        except Exception as e:
            logger.error(f"diagnose_fault failed: {e}", exc_info=True)
            return Result.fail(f"Fault diagnosis failed: {e}", code=500)

    # ------------------------------------------------------------------
    # get_fault_list
    # ------------------------------------------------------------------

    def get_fault_list(self) -> dict:
        """
        Return a list of all known fault types.

        Returns:
            Result dict with the fault list.
        """
        try:
            faults = self.fault_fixer.get_all_faults()
            return Result.ok(data={
                "total": len(faults),
                "faults": faults,
            })
        except Exception as e:
            logger.error(f"get_fault_list failed: {e}", exc_info=True)
            return Result.fail(f"Failed to get fault list: {e}", code=500)

    # ------------------------------------------------------------------
    # recommend_architecture
    # ------------------------------------------------------------------

    def recommend_architecture(self, device_count: int = 0,
                               daily_log_volume: int = 0,
                               budget: str = "",
                               team_skill: str = "") -> dict:
        """
        Recommend a log collection architecture based on environment scale.

        Uses arch_templates.json to match the right template.

        Args:
            device_count: Number of devices to collect from.
            daily_log_volume: Estimated daily log volume in GB.
            budget: Budget description ("low", "medium", "high").
            team_skill: Team skill level ("basic", "intermediate", "advanced").

        Returns:
            Result dict with the recommendation.
        """
        try:
            templates = JsonConfigLoader.load("arch_templates.json")
        except Exception as e:
            logger.warning(f"Could not load arch_templates.json: {e}")
            return Result.fail("Architecture templates not available", code=500)

        # Determine scale
        if device_count <= 10 or daily_log_volume <= 10:
            scale_key = "lightweight"
        elif device_count <= 100 or daily_log_volume <= 100:
            scale_key = "elk_cluster"
        else:
            scale_key = "enterprise_siem"

        # Fallback based on budget
        if budget and budget.lower() == "low":
            scale_key = "lightweight"
        elif budget and budget.lower() == "high" and scale_key != "enterprise_siem":
            scale_key = "elk_cluster"

        # Fallback based on team skill
        if team_skill and team_skill.lower() == "basic":
            scale_key = "lightweight"

        template = templates.get(scale_key)
        if template is None:
            return Result.fail(f"No architecture template found for scale {scale_key}", code=404)

        recommendation = dict(template)
        recommendation["recommended_scale"] = scale_key
        recommendation["device_count"] = device_count
        recommendation["daily_log_volume_gb"] = daily_log_volume

        # Add reasoning
        reasoning = []
        if device_count <= 10:
            reasoning.append("设备数量 ≤ 10 台，适合轻量级方案")
        elif device_count <= 100:
            reasoning.append("设备数量 11-100 台，适合分布式方案")
        else:
            reasoning.append("设备数量 > 100 台，需要企业级方案")

        if daily_log_volume <= 10:
            reasoning.append("日均日志量 ≤ 10GB，单机足以处理")
        elif daily_log_volume <= 100:
            reasoning.append("日均日志量 10-100GB，需要集群支持")
        else:
            reasoning.append("日均日志量 > 100GB，需要大规模集群")

        recommendation["reasoning"] = reasoning

        return Result.ok(data={
            "recommendation": recommendation,
            "input_parameters": {
                "device_count": device_count,
                "daily_log_volume_gb": daily_log_volume,
                "budget": budget,
                "team_skill": team_skill,
            },
        })