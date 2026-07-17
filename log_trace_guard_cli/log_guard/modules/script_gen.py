"""
Module 3: Script Generation

Provides regex generation, ES query generation, platform recommendation,
attack trace analysis, and script optimization for CLI-based log analysis.
"""

import json
import logging
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type

from log_guard.common.utils import JsonConfigLoader, LogManager, Result

logger = LogManager.get_logger("script_gen")


# ---------------------------------------------------------------------------
# BaseScriptStrategy
# ---------------------------------------------------------------------------

class BaseScriptStrategy(ABC):
    """Abstract base strategy for script generation."""

    strategy_type: str = "base"

    @abstractmethod
    def generate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate script / query / recommendation based on the given parameters.

        Args:
            params: Strategy-specific parameters dict.

        Returns:
            A dict with the generated output.
        """
        ...


# ---------------------------------------------------------------------------
# RegexGenStrategy
# ---------------------------------------------------------------------------

class RegexGenStrategy(BaseScriptStrategy):
    """Strategy for generating regex detection patterns from scenario descriptions."""

    strategy_type = "regex"

    def __init__(self) -> None:
        self._keywords: Dict[str, Any] = {}
        self._templates: Dict[str, Any] = {}
        self._fallback_rules: Dict[str, Any] = {}

    def _load_data(self) -> None:
        """Load all required JSON data files on first access."""
        if not self._keywords:
            self._keywords = JsonConfigLoader.load("script_gen_scene_keywords.json")
        if not self._templates:
            self._templates = JsonConfigLoader.load("script_gen_regex.json")
        if not self._fallback_rules:
            self._fallback_rules = JsonConfigLoader.load("script_gen_fallback_rules.json")

    def generate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate regex patterns from a scenario description.

        Args:
            params: Must contain at least 'scenario' (str).
                    Optional: 'log_sample' (str), 'device_type' (str).

        Returns:
            dict with keys: regexes (list), scenario (str), note (str).
        """
        self._load_data()

        scenario = params.get("scenario", "").strip()
        log_sample = params.get("log_sample", "")
        device_type = params.get("device_type", "")

        if not scenario:
            return {
                "regexes": [],
                "scenario": "",
                "note": "No scenario provided — cannot generate regex.",
            }

        scene_type = self._identify_scene(scenario)
        templates = self._templates.get(scene_type, [])
        fallback = self._get_fallback_rules(scene_type, scenario)

        regexes: List[Dict[str, Any]] = []

        # Use primary templates if available
        for tpl in templates:
            regexes.append({
                "name": tpl.get("name", "Unnamed rule"),
                "pattern": tpl.get("pattern", ""),
                "description": tpl.get("description", ""),
                "match_example": tpl.get("match_example", ""),
                "priority": tpl.get("priority", 50),
                "source": "template",
            })

        # Append fallback rules (deduplicated by name)
        seen_names = {r["name"] for r in regexes}
        for rule in fallback:
            if rule.get("name") not in seen_names:
                template = rule.get("pattern_template", "")
                if template and "{scenario_escaped}" in template:
                    escaped = re.escape(scenario[:60])
                    pattern = template.replace("{scenario_escaped}", escaped)
                else:
                    pattern = rule.get("pattern", "")
                regexes.append({
                    "name": rule.get("name", "Fallback rule"),
                    "pattern": pattern,
                    "description": rule.get("description", ""),
                    "match_example": rule.get("match_example", ""),
                    "priority": rule.get("priority", 50),
                    "source": "fallback",
                })

        # Build note
        note_parts: List[str] = []
        if scene_type != "default":
            note_parts.append(f"Detected scene type: {scene_type}")
        note_parts.append(f"Generated {len(regexes)} regex pattern(s).")
        if log_sample:
            note_parts.append("Log sample provided — patterns may need tuning.")
        if device_type:
            note_parts.append(f"Target device type: {device_type}")

        return {
            "regexes": regexes,
            "scenario": scenario,
            "note": " | ".join(note_parts),
        }

    def _identify_scene(self, scenario: str) -> str:
        """
        Identify the scene type from the scenario description using keyword matching.

        Returns a scene key (e.g. 'ssh', 'web', 'sql', 'port_scan', etc.)
        or 'default' if no match.
        """
        self._load_data()
        scenario_lower = scenario.lower()

        # Check regex scene keywords
        scene_keywords = self._keywords.get("regex", {})
        best_match = "default"
        best_score = 0

        for scene_type, keywords in scene_keywords.items():
            score = sum(1 for kw in keywords if kw.lower() in scenario_lower)
            if score > best_score:
                best_score = score
                best_match = scene_type

        return best_match

    def _get_fallback_rules(self, scene_type: str, scenario: str) -> List[Dict[str, Any]]:
        """
        Get fallback rules for a given scene type, falling back to 'default'.

        Returns a list of rule dicts.
        """
        self._load_data()
        rules = self._fallback_rules.get(scene_type, [])
        if not rules:
            rules = self._fallback_rules.get("default", [])
        return rules


# ---------------------------------------------------------------------------
# EsQueryGenStrategy
# ---------------------------------------------------------------------------

class EsQueryGenStrategy(BaseScriptStrategy):
    """Strategy for generating Elasticsearch queries from search scenarios."""

    strategy_type = "es_query"

    def __init__(self) -> None:
        self._templates: Dict[str, Any] = {}
        self._time_map: Dict[str, Any] = {}

    def _load_data(self) -> None:
        if not self._templates:
            self._templates = JsonConfigLoader.load("script_gen_es_queries.json")
        if not self._time_map:
            self._time_map = JsonConfigLoader.load("script_gen_time_map.json")

    def generate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate an ES query from a search scenario description.

        Args:
            params: Must contain 'search_scenario' (str).
                    Optional: 'index_pattern' (str), 'time_range' (str),
                              'filters' (list of dicts).

        Returns:
            dict with keys: query (dict), index_pattern (str),
                            time_range (str), note (str).
        """
        self._load_data()

        search_scenario = params.get("search_scenario", "").strip()
        index_pattern = params.get("index_pattern", "logs-*")
        time_range = params.get("time_range", "last_24h")
        filters = params.get("filters", [])

        if not search_scenario:
            return {
                "query": {},
                "index_pattern": index_pattern,
                "time_range": time_range,
                "note": "No search scenario provided — cannot generate query.",
            }

        # Identify best matching template
        scene_lower = search_scenario.lower()
        es_keywords = JsonConfigLoader.load("script_gen_scene_keywords.json").get("es_query", {})

        best_match = None
        best_score = 0
        for scene_key, keywords in es_keywords.items():
            score = sum(1 for kw in keywords if kw.lower() in scene_lower)
            if score > best_score:
                best_score = score
                best_match = scene_key

        # Build query from template or create a simple one
        if best_match and best_match in self._templates:
            template_data = self._templates[best_match]
            query = template_data.get("query_template", {})
            scene_label = template_data.get("scene_label", best_match)
            explanation = template_data.get("explanation", "")
        else:
            query = {
                "query": {
                    "bool": {
                        "must": [
                            {"match": {"message": search_scenario}}
                        ],
                        "filter": []
                    }
                },
                "size": 100
            }
            scene_label = "Custom query"
            explanation = "Generated from scenario description without template match."

        # Apply user filters
        if filters:
            if "filter" in query.get("query", {}).get("bool", {}):
                for f in filters:
                    query["query"]["bool"]["filter"].append(f)

        # Add time range filter if not already present
        resolved_time = self._time_map.get(time_range, self._time_map.get("default", "now-24h"))
        has_time = False
        bool_part = query.get("query", {}).get("bool", {})
        existing_filters = bool_part.get("filter", [])
        for ef in existing_filters:
            if "range" in ef and "@timestamp" in ef.get("range", {}):
                has_time = True
                break
        if not has_time:
            if "filter" not in bool_part:
                bool_part["filter"] = []
            bool_part["filter"].append({
                "range": {"@timestamp": {"gte": resolved_time, "lte": "now"}}
            })

        note = (
            f"Matched template: {scene_label} | "
            f"Explanation: {explanation} | "
            f"Index: {index_pattern} | "
            f"Time range: {time_range} ({resolved_time})"
        )

        return {
            "query": query,
            "index_pattern": index_pattern,
            "time_range": time_range,
            "note": note,
        }


# ---------------------------------------------------------------------------
# PlatformStrategy
# ---------------------------------------------------------------------------

class PlatformStrategy(BaseScriptStrategy):
    """Strategy for recommending log analysis platforms based on requirements."""

    strategy_type = "platform"

    def __init__(self) -> None:
        self._platforms: List[Dict[str, Any]] = []
        self._fallback: Dict[str, Any] = {}

    def _load_data(self) -> None:
        if not self._platforms:
            self._platforms = JsonConfigLoader.load("script_gen_platforms.json")
        if not self._fallback:
            self._fallback = JsonConfigLoader.load("script_gen_platform_fallback.json")

    def _classify_volume(self, daily_log_volume: str) -> List[str]:
        """Map volume string to supported volume categories."""
        vol_lower = daily_log_volume.lower()
        if any(v in vol_lower for v in ["tb", "large", "高"]):
            return ["large", "medium"]
        elif any(v in vol_lower for v in ["gb", "medium", "中"]):
            return ["medium", "small"]
        else:
            return ["small"]

    def _classify_budget(self, budget: str) -> List[str]:
        """Map budget string to budget level categories."""
        budget_lower = budget.lower()
        if any(b in budget_lower for b in ["high", "高", "unlimited"]):
            return ["high", "medium"]
        elif any(b in budget_lower for b in ["medium", "中"]):
            return ["medium", "low"]
        else:
            return ["low"]

    def _classify_skill(self, team_skill: str) -> List[str]:
        """Map team skill string to skill level categories."""
        skill_lower = team_skill.lower()
        if any(s in skill_lower for s in ["advanced", "high", "高", "expert"]):
            return ["advanced", "intermediate"]
        elif any(s in skill_lower for s in ["intermediate", "medium", "中"]):
            return ["intermediate", "basic"]
        else:
            return ["basic"]

    def generate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recommend log analysis platforms.

        Args:
            params: Must contain 'device_count' (int), 'daily_log_volume' (str),
                    'budget' (str), 'team_skill' (str).
                    Optional: 'requirements' (list of str).

        Returns:
            dict with keys: recommendations (list), comparison_table (list),
                            choice (str).
        """
        self._load_data()

        device_count = int(params.get("device_count", 10))
        daily_log_volume = params.get("daily_log_volume", "small")
        budget = params.get("budget", "medium")
        team_skill = params.get("team_skill", "basic")
        requirements = params.get("requirements", [])

        volume_cats = self._classify_volume(daily_log_volume)
        budget_cats = self._classify_budget(budget)
        skill_cats = self._classify_skill(team_skill)

        scored: List[tuple[float, Dict[str, Any]]] = []

        for platform in self._platforms:
            score = 0.0

            # Device range match
            dr = platform.get("device_range", {})
            if dr.get("min", 0) <= device_count <= dr.get("max", 999999):
                score += 3.0
            elif device_count < dr.get("min", 0):
                score += 1.0  # under-spec, still possible
            else:
                score -= 1.0  # over-spec

            # Volume match
            supported = platform.get("supported_volumes", [])
            vol_match = sum(1 for v in volume_cats if v in supported)
            score += vol_match * 2.0

            # Budget match
            budget_levels = platform.get("budget_level", [])
            budget_match = sum(1 for b in budget_cats if b in budget_levels)
            score += budget_match * 2.0

            # Skill match
            required_skill = platform.get("required_skill", [])
            skill_match = sum(1 for s in skill_cats if s in required_skill)
            score += skill_match * 1.5

            # Requirement match
            platform_features = set(platform.get("features", []))
            user_reqs_lower = set(r.lower() for r in requirements)
            feat_match = sum(
                1 for f in platform_features if any(r in f.lower() for r in user_reqs_lower)
            )
            score += feat_match * 1.0

            scored.append((score, platform))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)

        recommendations = []
        comparison_table = []
        for score, platform in scored:
            entry = {
                "name": platform.get("name", ""),
                "type": platform.get("type", ""),
                "score": round(score, 1),
                "pros": platform.get("pros", []),
                "cons": platform.get("cons", []),
                "estimated_cost": platform.get("estimated_cost", ""),
                "suitable_scenario": platform.get("suitable_scenario", ""),
            }
            recommendations.append(entry)
            comparison_table.append({
                "name": platform.get("name", ""),
                "type": platform.get("type", ""),
                "score": round(score, 1),
                "features": ", ".join(platform.get("features", [])[:3]),
            })

        # Top recommendation
        if recommendations:
            best = recommendations[0]
            choice = (
                f"Recommended: {best['name']} "
                f"(score: {best['score']}) — {best['suitable_scenario']}"
            )
        else:
            # Fallback to default platform
            fallback_name = self._fallback.get("name", "ELK Stack")
            choice = (
                f"Fallback recommendation: {fallback_name} — "
                f"{self._fallback.get('suitable_scenario', '')}"
            )
            recommendations.append({
                "name": fallback_name,
                "type": self._fallback.get("type", ""),
                "score": 0.0,
                "pros": self._fallback.get("pros", []),
                "cons": self._fallback.get("cons", []),
                "estimated_cost": self._fallback.get("estimated_cost", ""),
                "suitable_scenario": self._fallback.get("suitable_scenario", ""),
            })

        return {
            "recommendations": recommendations,
            "comparison_table": comparison_table,
            "choice": choice,
        }


# ---------------------------------------------------------------------------
# TraceStrategy
# ---------------------------------------------------------------------------

class TraceStrategy(BaseScriptStrategy):
    """Strategy for generating attack trace analysis from logs."""

    strategy_type = "trace"

    def __init__(self) -> None:
        self._trace_patterns: Dict[str, Any] = {}

    def _load_data(self) -> None:
        if not self._trace_patterns:
            self._trace_patterns = JsonConfigLoader.load("script_gen_trace_patterns.json")

    def generate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate an attack trace analysis.

        Args:
            params: Must contain 'logs' (list of str) and 'attack_type' (str).
                    Optional: 'start_time' (str), 'end_time' (str).

        Returns:
            dict with keys: attack_chain (list), timeline (list),
                            summary (str).
        """
        self._load_data()

        logs = params.get("logs", [])
        attack_type = params.get("attack_type", "").strip()
        start_time = params.get("start_time", "")
        end_time = params.get("end_time", "")

        attack_stages = self._trace_patterns.get("attack_stages", [])
        attack_patterns = self._trace_patterns.get("attack_patterns", {})
        risk_levels = self._trace_patterns.get("risk_levels", {})
        event_descriptions = self._trace_patterns.get("event_descriptions", {})

        # Determine the attack pattern key
        pattern_key = attack_type.lower().replace(" ", "_")
        if pattern_key not in attack_patterns:
            # Try partial match
            for key in attack_patterns:
                if key in attack_type.lower() or attack_type.lower() in key:
                    pattern_key = key
                    break
            else:
                pattern_key = "brute_force"  # fallback

        main_pattern = attack_patterns.get(pattern_key, attack_patterns.get("brute_force", ""))

        # Build attack chain stages
        attack_chain = []
        matched_events = []
        for stage in attack_stages:
            stage_events = []
            for log_line in logs:
                if main_pattern and re.search(main_pattern, log_line, re.IGNORECASE):
                    stage_events.append(log_line[:200])  # truncate
            if stage_events:
                attack_chain.append({
                    "stage": stage,
                    "event_count": len(stage_events),
                    "events": stage_events[:5],  # keep first 5
                })
                matched_events.extend(stage_events)
            else:
                attack_chain.append({
                    "stage": stage,
                    "event_count": 0,
                    "events": [],
                })

        # Build timeline from matched events
        timeline = []
        for i, evt in enumerate(matched_events[:20]):
            timeline.append({
                "sequence": i + 1,
                "event": evt[:150],
                "stage": attack_chain[i % len(attack_chain)]["stage"] if attack_chain else "",
                "description": event_descriptions.get(pattern_key, attack_type),
            })

        # Determine risk level
        risk_level = "medium"
        for level, keys in risk_levels.items():
            if pattern_key in keys:
                risk_level = level
                break

        # Summary
        total_matched = len(matched_events)
        summary = (
            f"Attack type: {attack_type} | "
            f"Risk level: {risk_level.upper()} | "
            f"Total matched events: {total_matched} | "
            f"Stages covered: {sum(1 for s in attack_chain if s['event_count'] > 0)}/{len(attack_stages)} | "
            f"Description: {event_descriptions.get(pattern_key, attack_type)}"
        )
        if start_time and end_time:
            summary += f" | Time range: {start_time} to {end_time}"

        return {
            "attack_chain": attack_chain,
            "timeline": timeline,
            "summary": summary,
        }


# ---------------------------------------------------------------------------
# ScriptStrategyFactory
# ---------------------------------------------------------------------------

class ScriptStrategyFactory:
    """Factory for registering and retrieving script generation strategies."""

    def __init__(self) -> None:
        self._strategies: Dict[str, Type[BaseScriptStrategy]] = {}
        self._instances: Dict[str, BaseScriptStrategy] = {}

    def register(self, name: str, strategy_class: Type[BaseScriptStrategy]) -> None:
        """Register a strategy class under a given name."""
        self._strategies[name] = strategy_class

    def get_strategy(self, name: str) -> BaseScriptStrategy:
        """
        Get (or create) a strategy instance by name.

        Args:
            name: Strategy registration name (e.g. 'regex', 'es_query').

        Returns:
            An instance of the registered strategy class.

        Raises:
            ValueError: If the strategy name is not registered.
        """
        if name not in self._strategies:
            raise ValueError(f"Unknown strategy: {name!r}. Registered: {list(self._strategies.keys())}")

        if name not in self._instances:
            self._instances[name] = self._strategies[name]()
        return self._instances[name]

    @property
    def registered_strategies(self) -> List[str]:
        """Return list of registered strategy names."""
        return list(self._strategies.keys())


# ---------------------------------------------------------------------------
# Default strategy registration
# ---------------------------------------------------------------------------

_default_factory: Optional[ScriptStrategyFactory] = None


def _register_default_strategies() -> ScriptStrategyFactory:
    """Create the default factory and register all built-in strategies."""
    factory = ScriptStrategyFactory()
    factory.register("regex", RegexGenStrategy)
    factory.register("es_query", EsQueryGenStrategy)
    factory.register("platform", PlatformStrategy)
    factory.register("trace", TraceStrategy)
    return factory


def get_default_factory() -> ScriptStrategyFactory:
    """Get or create the default strategy factory with all built-in strategies."""
    global _default_factory
    if _default_factory is None:
        _default_factory = _register_default_strategies()
    return _default_factory


# Register at module level
_default_factory = _register_default_strategies()


# ---------------------------------------------------------------------------
# ScriptGenService
# ---------------------------------------------------------------------------

class ScriptGenService:
    """
    High-level service for script generation, platform recommendation,
    attack trace analysis, and script optimization.

    Provides the same business logic as the original FastAPI project,
    adapted for CLI usage.
    """

    def __init__(self, factory: Optional[ScriptStrategyFactory] = None) -> None:
        self.factory = factory or get_default_factory()

    # ------------------------------------------------------------------
    # generate_regex
    # ------------------------------------------------------------------

    def generate_regex(
        self,
        scenario: str,
        log_sample: Optional[str] = None,
        device_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate regex detection rules from a scenario description.

        Args:
            scenario: Attack or event scenario description.
            log_sample: Optional sample log line for context.
            device_type: Optional device type hint (e.g. 'ssh', 'web').

        Returns:
            Result dict with generated regex patterns.
        """
        try:
            strategy = self.factory.get_strategy("regex")
            params: Dict[str, Any] = {"scenario": scenario}
            if log_sample:
                params["log_sample"] = log_sample
            if device_type:
                params["device_type"] = device_type
            result = strategy.generate(params)
            return Result.ok(
                data=result,
                msg=f"Generated {len(result.get('regexes', []))} regex pattern(s)",
            )
        except Exception as e:
            logger.error(f"Regex generation failed: {e}", exc_info=True)
            return Result.fail(msg=f"Regex generation failed: {e}")

    # ------------------------------------------------------------------
    # generate_regex_batch
    # ------------------------------------------------------------------

    def generate_regex_batch(self, scenarios: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate regex patterns for multiple scenarios.

        Args:
            scenarios: List of dicts, each with 'scenario' key and optional
                       'log_sample' and 'device_type' keys.

        Returns:
            Result dict with a list of generated results.
        """
        try:
            strategy = self.factory.get_strategy("regex")
            results = []
            for item in scenarios:
                params = {
                    "scenario": item.get("scenario", ""),
                }
                if item.get("log_sample"):
                    params["log_sample"] = item["log_sample"]
                if item.get("device_type"):
                    params["device_type"] = item["device_type"]
                results.append(strategy.generate(params))
            return Result.ok(
                data={"results": results, "count": len(results)},
                msg=f"Generated regex for {len(results)} scenario(s)",
            )
        except Exception as e:
            logger.error(f"Batch regex generation failed: {e}", exc_info=True)
            return Result.fail(msg=f"Batch regex generation failed: {e}")

    # ------------------------------------------------------------------
    # generate_es_query
    # ------------------------------------------------------------------

    def generate_es_query(
        self,
        search_scenario: str,
        index_pattern: Optional[str] = "logs-*",
        time_range: Optional[str] = "last_24h",
        filters: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Generate an Elasticsearch query from a search scenario.

        Args:
            search_scenario: Description of the search scenario.
            index_pattern: Elasticsearch index pattern (default: 'logs-*').
            time_range: Time range label (e.g. 'last_1h', 'last_24h').
            filters: Optional list of additional ES filter dicts.

        Returns:
            Result dict with the generated ES query.
        """
        try:
            strategy = self.factory.get_strategy("es_query")
            params: Dict[str, Any] = {
                "search_scenario": search_scenario,
                "index_pattern": index_pattern or "logs-*",
                "time_range": time_range or "last_24h",
                "filters": filters or [],
            }
            result = strategy.generate(params)
            return Result.ok(
                data=result,
                msg=f"Generated ES query for: {search_scenario[:60]}",
            )
        except Exception as e:
            logger.error(f"ES query generation failed: {e}", exc_info=True)
            return Result.fail(msg=f"ES query generation failed: {e}")

    # ------------------------------------------------------------------
    # generate_es_query_batch
    # ------------------------------------------------------------------

    def generate_es_query_batch(
        self, queries: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate ES queries for multiple search scenarios.

        Args:
            queries: List of dicts, each with 'search_scenario' key and
                     optional 'index_pattern', 'time_range', 'filters'.

        Returns:
            Result dict with a list of generated queries.
        """
        try:
            strategy = self.factory.get_strategy("es_query")
            results = []
            for item in queries:
                params: Dict[str, Any] = {
                    "search_scenario": item.get("search_scenario", ""),
                    "index_pattern": item.get("index_pattern", "logs-*"),
                    "time_range": item.get("time_range", "last_24h"),
                    "filters": item.get("filters", []),
                }
                results.append(strategy.generate(params))
            return Result.ok(
                data={"results": results, "count": len(results)},
                msg=f"Generated ES queries for {len(results)} scenario(s)",
            )
        except Exception as e:
            logger.error(f"Batch ES query generation failed: {e}", exc_info=True)
            return Result.fail(msg=f"Batch ES query generation failed: {e}")

    # ------------------------------------------------------------------
    # recommend_platform
    # ------------------------------------------------------------------

    def recommend_platform(
        self,
        device_count: int,
        daily_log_volume: str,
        budget: str,
        team_skill: str,
        requirements: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Recommend log analysis platforms based on requirements.

        Args:
            device_count: Number of devices generating logs.
            daily_log_volume: 'small', 'medium', or 'large'.
            budget: 'low', 'medium', or 'high'.
            team_skill: 'basic', 'intermediate', or 'advanced'.
            requirements: Optional list of specific feature requirements.

        Returns:
            Result dict with platform recommendations.
        """
        try:
            strategy = self.factory.get_strategy("platform")
            params: Dict[str, Any] = {
                "device_count": device_count,
                "daily_log_volume": daily_log_volume,
                "budget": budget,
                "team_skill": team_skill,
                "requirements": requirements or [],
            }
            result = strategy.generate(params)
            recommendations = result.get("recommendations", [])
            return Result.ok(
                data=result,
                msg=f"Found {len(recommendations)} platform recommendation(s)",
            )
        except Exception as e:
            logger.error(f"Platform recommendation failed: {e}", exc_info=True)
            return Result.fail(msg=f"Platform recommendation failed: {e}")

    # ------------------------------------------------------------------
    # trace_attack
    # ------------------------------------------------------------------

    def trace_attack(
        self,
        logs: List[str],
        attack_type: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Trace an attack through log events.

        Args:
            logs: List of raw log lines.
            attack_type: Type of attack (e.g. 'brute_force', 'sql_injection').
            start_time: Optional start time for filtering.
            end_time: Optional end time for filtering.

        Returns:
            Result dict with attack chain, timeline, and summary.
        """
        try:
            strategy = self.factory.get_strategy("trace")
            params: Dict[str, Any] = {
                "logs": logs,
                "attack_type": attack_type,
                "start_time": start_time or "",
                "end_time": end_time or "",
            }
            result = strategy.generate(params)
            return Result.ok(
                data=result,
                msg=f"Attack trace generated for: {attack_type}",
            )
        except Exception as e:
            logger.error(f"Attack trace failed: {e}", exc_info=True)
            return Result.fail(msg=f"Attack trace failed: {e}")

    # ------------------------------------------------------------------
    # optimize_script
    # ------------------------------------------------------------------

    def optimize_script(
        self,
        script: str,
        script_type: str,
        scenario: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Optimize and score a detection script (regex or ES query).

        For regex:
          - Validate syntax via re.compile
          - Check for (?i) case-insensitive flag
          - Check for excessive .* /.+ wildcards
          - Check for capture groups
          - Score from script_gen_scoring.json

        For es_query:
          - Validate JSON
          - Check for top-level query field
          - Check size limits

        Args:
            script: The script content (regex pattern string or JSON string).
            script_type: 'regex' or 'es_query'.
            scenario: Optional scenario description for context.

        Returns:
            Result dict with issues, suggestions, score, and optimized_script.
        """
        try:
            scoring = JsonConfigLoader.load("script_gen_scoring.json")

            if script_type == "regex":
                return self._optimize_regex(script, scenario, scoring)
            elif script_type == "es_query":
                return self._optimize_es_query(script, scenario, scoring)
            else:
                return Result.fail(
                    msg=f"Unsupported script type: {script_type!r}. "
                    f"Supported: 'regex', 'es_query'."
                )
        except Exception as e:
            logger.error(f"Script optimization failed: {e}", exc_info=True)
            return Result.fail(msg=f"Script optimization failed: {e}")

    def _optimize_regex(
        self,
        script: str,
        scenario: Optional[str],
        scoring: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Optimize a regex pattern script."""
        regex_config = scoring.get("regex", {})
        base_score = regex_config.get("base_score", 50)
        score_min = regex_config.get("score_min", 0)
        score_max = regex_config.get("score_max", 100)

        issues: List[str] = []
        suggestions: List[str] = []
        score = base_score
        optimized = script

        # 1. Validate syntax
        try:
            re.compile(script)
            score += regex_config.get("compile_pass_bonus", 20)
        except re.error as e:
            issues.append(f"Regex syntax error: {e}")
            suggestions.append("Fix the regex syntax error before use.")
            score = score_min

        if score <= score_min:
            return Result.fail(
                msg="Regex syntax validation failed",
                data={
                    "issues": issues,
                    "suggestions": suggestions,
                    "score": score_min,
                    "optimized_script": script,
                },
            )

        # 2. Check for (?i) case-insensitive flag
        if not re.search(r"\(\?i\)", script):
            suggestions.append(regex_config.get("case_insensitive_suggest",
                                                "建议添加 (?i) 大小写不敏感标志，避免漏报"))
            issues.append("Missing (?i) case-insensitive flag")

        # 3. Check for excessive .* /.+
        wildcard_matches = re.findall(r"\.\*|\.\+", script)
        threshold = regex_config.get("wildcard_excessive_threshold", 3)
        if len(wildcard_matches) > threshold:
            penalty = regex_config.get("wildcard_excessive_penalty", 10)
            score -= penalty
            issues.append(regex_config.get("wildcard_excessive_issue",
                                           "包含过多 .* 或 .+，可能导致性能问题或误报"))
            suggestions.append("考虑使用更具体的字符类或限定符替代 .*")
        elif len(wildcard_matches) > 0:
            score += regex_config.get("wildcard_reasonable_bonus", 5)

        # 4. Check for capture groups
        if "(" in script and ")" in script:
            score += regex_config.get("capture_group_bonus", 0)
            # Check if using named groups or plain groups
            if not re.search(r"\(\?P<", script):
                suggestions.append(regex_config.get("capture_group_suggest",
                                                    "建议使用捕获组 () 提取关键字段，便于后续分析"))

        # 5. Check for character classes
        if re.search(r"\[.*?\]", script):
            score += regex_config.get("char_class_bonus", 5)

        # 6. Check length
        length = len(script)
        long_threshold = regex_config.get("length_long_threshold", 200)
        if length > long_threshold:
            penalty = regex_config.get("length_long_penalty", 10)
            score -= penalty
            issues.append(regex_config.get("length_long_issue",
                                           "正则表达式过长，建议拆分或简化"))
        min_threshold = regex_config.get("length_min_threshold", 10)
        if length >= min_threshold:
            score += regex_config.get("length_min_bonus", 10)

        # Clamp score
        score = max(score_min, min(score, score_max))

        # Build suggestion to add (?i) if missing
        if not re.search(r"\(\?i\)", script):
            optimized = f"(?i){script}"

        data = {
            "issues": issues,
            "suggestions": suggestions,
            "score": score,
            "optimized_script": optimized,
            "script_type": "regex",
        }
        if scenario:
            data["scenario"] = scenario

        level = "good" if score >= 80 else ("fair" if score >= 50 else "poor")
        return Result.ok(data=data, msg=f"Regex optimization complete (score={score}, {level})")

    def _optimize_es_query(
        self,
        script: str,
        scenario: Optional[str],
        scoring: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Optimize an ES query script."""
        es_config = scoring.get("es_query", {})
        base_score = es_config.get("base_score", 50)
        score_min = es_config.get("score_min", 0)
        score_max = es_config.get("score_max", 100)

        issues: List[str] = []
        suggestions: List[str] = []
        score = base_score
        optimized = script

        # 1. Validate JSON
        try:
            parsed = json.loads(script)
            score += es_config.get("json_parse_bonus", 20)
        except json.JSONDecodeError as e:
            issues.append(f"JSON parse error: {e}")
            suggestions.append("Fix the JSON syntax error before use.")
            return Result.fail(
                msg="ES query JSON validation failed",
                data={
                    "issues": issues,
                    "suggestions": suggestions,
                    "score": score_min,
                    "optimized_script": script,
                },
            )

        # 2. Check for top-level query field
        if "query" in parsed:
            score += es_config.get("query_field_bonus", 10)
        else:
            issues.append(es_config.get("query_field_missing_issue",
                                         "缺少顶级 query 字段"))
            suggestions.append("Add a top-level 'query' field to the ES query body.")

        # 3. Check size limit
        size = parsed.get("size", 0)
        size_limit = es_config.get("size_limit_threshold", 10000)
        if size > size_limit:
            penalty = es_config.get("size_limit_penalty", 10)
            score -= penalty
            issues.append(es_config.get("size_limit_issue",
                                         "size 超过 10000，建议使用滚动查询"))
            suggestions.append("Use scroll API or set size <= 10000 for basic queries.")

        # 4. Check for aggregations (bonus)
        if "aggs" in parsed:
            score += es_config.get("aggs_bonus", 10)

        # Clamp score
        score = max(score_min, min(score, score_max))

        data = {
            "issues": issues,
            "suggestions": suggestions,
            "score": score,
            "optimized_script": optimized,
            "script_type": "es_query",
        }
        if scenario:
            data["scenario"] = scenario

        level = "good" if score >= 80 else ("fair" if score >= 50 else "poor")
        return Result.ok(data=data, msg=f"ES query optimization complete (score={score}, {level})")