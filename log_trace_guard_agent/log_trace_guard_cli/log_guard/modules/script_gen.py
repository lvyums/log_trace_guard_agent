"""
Module 3: Script Generation

Provides regex generation, ES query generation,
attack trace analysis, and script optimization for CLI-based log analysis.
"""

import json
import logging
import os
import re
import urllib.request
import urllib.error
import urllib.parse
import base64
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, Tuple

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
# ES 集群连接配置管理
# ---------------------------------------------------------------------------


def _es_config_path() -> str:
    """获取 ES 配置文件路径 ~/.log-guard/config.json"""
    home = os.path.expanduser("~")
    cfg_dir = os.path.join(home, ".log-guard")
    os.makedirs(cfg_dir, exist_ok=True)
    return os.path.join(cfg_dir, "config.json")


def load_es_config() -> dict:
    """从 ~/.log-guard/config.json 加载 ES 连接配置"""
    path = _es_config_path()
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("es", {})
    except Exception:
        return {}


def save_es_config(host: str, port: int = 9200, scheme: str = "http",
                   user: str = "", password: str = "") -> str:
    """保存 ES 连接配置到 ~/.log-guard/config.json"""
    path = _es_config_path()
    data = {}
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
    data["es"] = {
        "host": host,
        "port": port,
        "scheme": scheme,
        "user": user,
        "password": password,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def _es_base_url(cfg: dict) -> Optional[str]:
    """根据 ES 配置构建 base URL"""
    host = cfg.get("host", "").strip()
    if not host:
        return None
    port = cfg.get("port", 9200)
    scheme = cfg.get("scheme", "http")
    return f"{scheme}://{host}:{port}"


def _es_auth_header(cfg: dict) -> Optional[dict]:
    """如果配置了用户名密码，生成 Authorization header"""
    user = cfg.get("user", "").strip()
    password = cfg.get("password", "").strip()
    if user and password:
        token = base64.b64encode(f"{user}:{password}".encode()).decode()
        return {"Authorization": f"Basic {token}"}
    return None


def execute_es_query(query_dict: dict, index_pattern: str = "logs-*",
                     es_config: Optional[dict] = None,
                     size: int = 20) -> dict:
    """向 ES 集群发送查询并返回结果

    Args:
        query_dict: ES Query DSL dict
        index_pattern: 索引模式
        es_config: ES 连接配置（不传则从 ~/.log-guard/config.json 读取）
        size: 返回结果条数

    Returns:
        dict with keys: success, hits (int), total (int), samples (list),
                        took_ms (int), error (str)
    """
    cfg = es_config or load_es_config()
    base_url = _es_base_url(cfg)
    if not base_url:
        return {"success": False, "hits": 0, "samples": [], "error": "ES 未配置，请先配置 ES 连接信息"}

    # 构建请求 URL
    url = f"{base_url}/{index_pattern}/_search"
    headers = {"Content-Type": "application/json"}
    auth_header = _es_auth_header(cfg)
    if auth_header:
        headers.update(auth_header)

    # 限制返回条数
    body = dict(query_dict)
    body["size"] = size

    try:
        req_data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(url, data=req_data, headers=headers, method="POST")
        import time
        start = time.time()
        with urllib.request.urlopen(req, timeout=30) as resp:
            elapsed = int((time.time() - start) * 1000)
            raw = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")[:500]
        return {"success": False, "hits": 0, "samples": [],
                "error": f"ES HTTP {e.code}: {body_text}"}
    except urllib.error.URLError as e:
        return {"success": False, "hits": 0, "samples": [],
                "error": f"ES 连接失败: {e.reason}"}
    except Exception as e:
        return {"success": False, "hits": 0, "samples": [],
                "error": f"ES 查询异常: {e}"}

    # 解析结果
    total = raw.get("hits", {}).get("total", {}).get("value", 0)
    hits = raw.get("hits", {}).get("hits", [])
    samples = []
    for h in hits:
        src = h.get("_source", {})
        samples.append({
            "index": h.get("_index", ""),
            "id": h.get("_id", ""),
            "score": h.get("_score", 0),
            "source": src,
            "preview": json.dumps(src, ensure_ascii=False)[:300],
        })

    return {
        "success": True,
        "hits": len(hits),
        "total": total,
        "samples": samples,
        "took_ms": elapsed,
        "timed_out": raw.get("timed_out", False),
        "shards": raw.get("_shards", {}),
    }


def test_regex_on_file(regexes: List[Dict[str, Any]], log_lines: List[str]) -> dict:
    """对日志文件内容测试正则规则匹配效果

    Args:
        regexes: 正则规则列表，每项含 name, pattern
        log_lines: 日志行列表

    Returns:
        dict with keys: total_lines (int), results (list)
    """
    results = []
    for rule in regexes:
        pattern = rule.get("pattern", "")
        name = rule.get("name", "Unnamed")
        if not pattern:
            results.append({"name": name, "pattern": pattern, "matched": 0,
                            "total": len(log_lines), "samples": [],
                            "error": "空白正则"})
            continue
        try:
            compiled = re.compile(pattern)
        except re.error as e:
            results.append({"name": name, "pattern": pattern, "matched": 0,
                            "total": len(log_lines), "samples": [],
                            "error": f"正则语法错误: {e}"})
            continue

        matched_lines = []
        for line_no, line in enumerate(log_lines, 1):
            if compiled.search(line):
                matched_lines.append({"line_no": line_no, "content": line[:200]})
                if len(matched_lines) >= 5:
                    break

        results.append({
            "name": name,
            "pattern": pattern,
            "matched": len(matched_lines),
            "total": len(log_lines),
            "samples": matched_lines,
            "error": None,
        })

    total_matched = sum(r["matched"] for r in results)
    return {
        "total_lines": len(log_lines),
        "total_rules": len(regexes),
        "total_matched": total_matched,
        "results": results,
    }
# ──────────────────────────────────────────────
# 溯源报告导出
# ──────────────────────────────────────────────


def export_trace_report(trace_data: dict, output_path: Optional[str] = None,
                        fmt: str = "markdown") -> dict:
    """将溯源结果导出为可读报告

    Args:
        trace_data: trace_attack() 返回的 data dict (含 attack_chain, timeline, summary)
        output_path: 输出路径，不传则自动生成
        fmt: 格式 markdown / json

    Returns:
        {"path": ..., "format": ..., "size": ...}
    """
    if not output_path:
        import time as _t
        ts = _t.strftime("%Y%m%d_%H%M%S")
        base = os.path.join(os.path.expanduser("~"), ".log-guard", "reports")
        os.makedirs(base, exist_ok=True)
        output_path = os.path.join(base, f"trace_report_{ts}.{fmt}")

    if fmt == "json":
        content = json.dumps(trace_data, ensure_ascii=False, indent=2)
    else:
        content = _build_markdown_report(trace_data)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    return {"path": output_path, "format": fmt, "size": len(content)}


def _build_markdown_report(data: dict) -> str:
    """构建 Markdown 格式溯源报告"""
    lines = []
    lines.append("# 🔍 攻击溯源报告")
    lines.append("")
    lines.append(f"**摘要**: {data.get('summary', '')}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 攻击链分析")
    lines.append("")

    attack_chain = data.get("attack_chain", [])
    for i, stage in enumerate(attack_chain, 1):
        stage_name = stage.get("stage", "?")
        count = stage.get("event_count", 0)
        icon = "🟢" if count > 0 else "⚪"
        lines.append(f"### {icon} 阶段 {i}: {stage_name}")
        lines.append("")
        lines.append(f"- 匹配事件数: **{count}**")
        if count > 0:
            lines.append("")
            lines.append("| # | 事件 |")
            lines.append("|---|------|")
            for j, evt in enumerate(stage.get("events", [])[:10], 1):
                lines.append(f"| {j} | `{evt[:200]}` |")
        lines.append("")

    timeline = data.get("timeline", [])
    if timeline:
        lines.append("---")
        lines.append("")
        lines.append("## 时间线")
        lines.append("")
        lines.append("| 序号 | 事件 | 阶段 |")
        lines.append("|------|------|------|")
        for t in timeline:
            lines.append(f"| {t.get('sequence', '?')} | `{t.get('event', '')[:120]}` | {t.get('stage', '')} |")
        lines.append("")

    lines.append("---")
    lines.append(f"*报告生成时间: {__import__('time').strftime('%Y-%m-%d %H:%M:%S')}*")
    return "\n".join(lines)


# ════════════════════════════════════════════
# ES 查询模板管理
# ════════════════════════════════════════════

_ES_TEMPLATES_PATH = os.path.join(os.path.expanduser("~"), ".log-guard", "es_templates.json")


def _ensure_es_templates() -> dict:
    """确保模板文件存在并返回当前模板字典"""
    os.makedirs(os.path.dirname(_ES_TEMPLATES_PATH), exist_ok=True)
    if not os.path.isfile(_ES_TEMPLATES_PATH):
        default = {
            "SSH爆破检测": {
                "scenario": "检测SSH爆破攻击",
                "index_pattern": "logs-*",
                "time_range": "last_24h",
                "query": {"query": {"bool": {"must": [{"bool": {"should": [
                    {"match_phrase": {"message": "Failed password"}},
                    {"match_phrase": {"message": "Invalid user"}}
                ]}}], "filter": [{"range": {"@timestamp": {"gte": "now-24h", "lte": "now"}}}]}}, "size": 0,
                "aggs": {"brute_force_ips": {"terms": {"field": "source.ip", "size": 20}}}}
            },
            "SQL注入检测": {
                "scenario": "检测SQL注入攻击",
                "index_pattern": "logs-*",
                "time_range": "last_24h",
                "query": {"query": {"bool": {"must": [{"bool": {"should": [
                    {"wildcard": {"url": {"value": "*union*select*"}}},
                    {"match": {"url": "1=1"}}
                ]}}, {"match": {"event.type": "http"}}], "filter": [{"range": {"@timestamp": {"gte": "now-24h", "lte": "now"}}}]}}, "size": 10}
            },
        }
        with open(_ES_TEMPLATES_PATH, "w", encoding="utf-8") as f:
            json.dump(default, f, ensure_ascii=False, indent=2)
        return default
    try:
        with open(_ES_TEMPLATES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def list_es_templates() -> list[dict]:
    """列出所有 ES 查询模板"""
    data = _ensure_es_templates()
    result = []
    for name, tpl in data.items():
        result.append({
            "name": name,
            "scenario": tpl.get("scenario", ""),
            "index_pattern": tpl.get("index_pattern", "logs-*"),
            "time_range": tpl.get("time_range", "last_24h"),
        })
    return result


def save_es_template(name: str, query_dict: dict, scenario: str = "",
                     index_pattern: str = "logs-*", time_range: str = "last_24h") -> str:
    """保存 ES 查询为命名模板"""
    data = _ensure_es_templates()
    data[name] = {
        "scenario": scenario,
        "index_pattern": index_pattern,
        "time_range": time_range,
        "query": query_dict,
    }
    with open(_ES_TEMPLATES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return name


def delete_es_template(name: str) -> bool:
    """删除命名模板"""
    data = _ensure_es_templates()
    if name not in data:
        return False
    del data[name]
    with open(_ES_TEMPLATES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return True


def load_es_template(name: str) -> Optional[dict]:
    """加载命名模板的 query dict"""
    data = _ensure_es_templates()
    tpl = data.get(name)
    if not tpl:
        return None
    return {
        "query": tpl.get("query", {}),
        "index_pattern": tpl.get("index_pattern", "logs-*"),
        "time_range": tpl.get("time_range", "last_24h"),
        "scenario": tpl.get("scenario", ""),
    }


# ════════════════════════════════════════════
# 溯源 → 监控规则（闭环）
# ════════════════════════════════════════════


def trace_to_monitoring_rules(trace_data: dict) -> dict:
    """从溯源结果自动生成持续监控规则

    根据攻击链中的 matched events，提取关键词和 IP，
    生成 ES 查询 DSL 和 正则检测规则，实现分析→监控的闭环。

    Args:
        trace_data: trace_attack() 返回的 data dict

    Returns:
        {"es_query": {...}, "regex_rules": [...], "summary": str}
    """
    # 提取关键词
    attack_chain = trace_data.get("attack_chain", [])
    timeline = trace_data.get("timeline", [])
    summary = trace_data.get("summary", "")

    keywords = set()
    ips = set()
    for stage in attack_chain:
        for evt in stage.get("events", []):
            # 提取 IP
            found_ips = re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", evt)
            for ip in found_ips:
                ips.add(ip)
            # 提取关键词（取常见的攻击特征词）
            for kw in ["Failed password", "Invalid user", "Accepted password",
                       "sudo", "COMMAND", "error", "warning", "login",
                       "SELECT", "UNION", "DROP", "exec", "eval",
                       "POST", "GET", "HTTP", "script", "alert"]:
                if kw.lower() in evt.lower():
                    keywords.add(kw)

    # 构建 ES 查询
    es_query = _build_es_from_keywords(list(keywords)[:10], list(ips)[:5])
    # 构建正则规则
    regex_rules = _build_regex_from_keywords(list(keywords)[:10], list(ips)[:5])

    return {
        "es_query": es_query,
        "regex_rules": regex_rules,
        "summary": summary,
        "keywords": sorted(keywords),
        "ips": sorted(ips),
        "source_attack_type": summary.split("|")[0].replace("Attack type:", "").strip() if "|" in summary else "unknown",
    }


def _build_es_from_keywords(keywords: list[str], ips: list[str]) -> dict:
    """根据关键词+IP列表生成 ES Query DSL"""
    should = []
    for kw in keywords[:8]:
        if kw and len(kw) > 2:
            should.append({"match_phrase": {"message": kw}})
    for ip in ips[:3]:
        should.append({"match_phrase": {"message": ip}})

    if not should:
        return {"query": {"match_all": {}}, "size": 10}

    return {
        "query": {
            "bool": {
                "must": [{"bool": {"should": should}}],
                "filter": [{"range": {"@timestamp": {"gte": "now-24h", "lte": "now"}}}]
            }
        },
        "size": 10,
    }


def _build_regex_from_keywords(keywords: list[str], ips: list[str]) -> list[dict]:
    """根据关键词+IP列表生成正则检测规则"""
    rules = []
    for kw in keywords[:8]:
        if not kw or len(kw) < 3:
            continue
        escaped = re.escape(kw)
        rules.append({
            "name": f"溯源自动规则: {kw[:30]}",
            "pattern": f"(?i){escaped}",
            "description": f"从攻击溯源自动生成的检测规则（关键词: {kw}）",
            "match_example": kw,
            "priority": 75,
            "source": "trace_to_rule",
        })
    for ip in ips[:3]:
        rules.append({
            "name": f"溯源自动规则: IP_{ip}",
            "pattern": re.escape(ip),
            "description": f"从攻击溯源自动生成的检测规则（IP: {ip}）",
            "match_example": ip,
            "priority": 85,
            "source": "trace_to_rule",
        })
    return rules


# ════════════════════════════════════════════
# Splunk 配置管理
# ════════════════════════════════════════════


def save_splunk_config(host: str = "", port: int = 8089, scheme: str = "https",
                       user: str = "", password: str = "") -> str:
    """保存 Splunk 连接配置到 ~/.log-guard/config.json"""
    path = _es_config_path()  # 同文件
    data = {}
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
    data["splunk"] = {
        "host": host,
        "port": port,
        "scheme": scheme,
        "user": user,
        "password": password,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def load_splunk_config() -> dict:
    """加载 Splunk 连接配置"""
    path = _es_config_path()
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("splunk", {})
    except Exception:
        return {}


def execute_splunk_query(spl_query: str, splunk_config: Optional[dict] = None,
                         max_results: int = 50, timeout: int = 30) -> dict:
    """向 Splunk 执行 SPL 查询

    使用 Splunk REST API: POST /services/search/jobs → 轮询 → GET results

    Args:
        spl_query: SPL 查询语句
        splunk_config: 连接配置（不传则从文件加载）
        max_results: 最大返回条数
        timeout: 超时秒数

    Returns:
        {"success": bool, "results": [...], "event_count": int, "error": str}
    """
    cfg = splunk_config or load_splunk_config()
    host = cfg.get("host", "").strip()
    if not host:
        return {"success": False, "results": [], "event_count": 0,
                "error": "Splunk 未配置，请先配置 Splunk 连接信息"}

    port = cfg.get("port", 8089)
    scheme = cfg.get("scheme", "https")
    user = cfg.get("user", "")
    password = cfg.get("password", "")
    base_url = f"{scheme}://{host}:{port}"

    # 基础认证
    auth_data = None
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    if user and password:
        import base64 as _b64
        token = _b64.b64encode(f"{user}:{password}".encode()).decode()
        headers["Authorization"] = f"Basic {token}"

    try:
        import time as _t
        # 1. 提交搜索任务
        import urllib.parse
        search_url = f"{base_url}/services/search/jobs"
        post_data = urllib.parse.urlencode({
            "search": spl_query,
            "max_count": str(max_results),
        }).encode("utf-8")

        req = urllib.request.Request(search_url, data=post_data, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")

        # 2. 从响应中提取 sid
        sid = ""
        for line in body.split("\n"):
            if "<sid>" in line or "sid" in line.lower():
                import xml.etree.ElementTree as ET
                try:
                    root = ET.fromstring(body)
                    ns = {"s": "http://www.w3.org/2005/Atom"}
                    sid_elem = root.find(".//s:entry//s:id", ns)
                    if sid_elem is not None:
                        sid = sid_elem.text or ""
                    else:
                        sid = root.findtext(".//sid", "")
                except Exception:
                    # 简单匹配
                    m = re.search(r"<sid[^>]*>([^<]+)</sid>", body)
                    if m:
                        sid = m.group(1)
                break

        if not sid:
            return {"success": False, "results": [], "event_count": 0,
                    "error": "无法从 Splunk 响应中提取 SID"}

        # 3. 轮询等待完成
        job_url = f"{base_url}/services/search/jobs/{sid}"
        deadline = _t.time() + timeout
        while _t.time() < deadline:
            status_req = urllib.request.Request(job_url, headers=headers)
            try:
                with urllib.request.urlopen(status_req, timeout=10) as sresp:
                    stext = sresp.read().decode("utf-8")
                if 'isDone">1<' in stext or '"isDone":"1"' in stext:
                    break
            except Exception:
                pass
            _t.sleep(1)
        else:
            return {"success": False, "results": [], "event_count": 0,
                    "error": f"Splunk 搜索超时（{timeout}s）"}

        # 4. 获取结果
        results_url = f"{base_url}/services/search/jobs/{sid}/results?count={max_results}&output_mode=json"
        results_req = urllib.request.Request(results_url, headers=headers)
        with urllib.request.urlopen(results_req, timeout=timeout) as rresp:
            rdata = json.loads(rresp.read().decode("utf-8"))

        results = rdata.get("results", [])
        return {
            "success": True,
            "results": results,
            "event_count": len(results),
            "sid": sid,
            "error": None,
        }

    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")[:500]
        return {"success": False, "results": [], "event_count": 0,
                "error": f"Splunk HTTP {e.code}: {body_text}"}
    except urllib.error.URLError as e:
        return {"success": False, "results": [], "event_count": 0,
                "error": f"Splunk 连接失败: {e.reason}"}
    except Exception as e:
        return {"success": False, "results": [], "event_count": 0,
                "error": f"Splunk 查询异常: {e}"}


# Splunk SPL 查询模板
_SPL_TEMPLATES = {
    "ssh_brute": {
        "scene_label": "SSH爆破攻击",
        "spl": 'index=* sourcetype=ssh* "Failed password" OR "Invalid user" | stats count by src_ip | where count > 5 | sort -count',
    },
    "sql_injection": {
        "scene_label": "SQL注入攻击",
        "spl": 'index=* sourcetype=access_* "union select" OR "1=1" OR "1=2" OR "%27" OR "--" | stats count by src_ip, uri_path | sort -count',
    },
    "web_attack": {
        "scene_label": "Web攻击事件",
        "spl": 'index=* sourcetype=access_* (status=403 OR status=404 OR status>=500) | stats count by src_ip, uri_path, status | sort -count',
    },
    "abnormal_traffic": {
        "scene_label": "异常流量检测",
        "spl": 'index=* sourcetype=netflow* bytes > 1000000 | stats sum(bytes) as total_bytes, count by src_ip | where total_bytes > 10000000 | sort -total_bytes',
    },
    "data_exfil": {
        "scene_label": "数据泄露检测",
        "spl": 'index=* ("INTO OUTFILE" OR mysqldump OR pg_dump OR export OR download) | stats count by user, src_ip | sort -count',
    },
}


def generate_splunk_query(search_scenario: str, index: str = "*",
                          time_range: str = "last_24h") -> dict:
    """根据场景描述生成 Splunk SPL 查询语句

    Args:
        search_scenario: 检索场景描述
        index: 索引名称
        time_range: 时间范围标签

    Returns:
        {"spl": ..., "scene_label": ..., "note": ..., "index": ..., "time_range": ...}
    """
    scene_lower = search_scenario.lower()

    best_match = None
    best_score = 0
    for key, tpl in _SPL_TEMPLATES.items():
        kw = key.replace("_", " ")
        # 同时匹配英文关键词和中文场景标签
        score = sum(1 for word in kw.split() if word in scene_lower)
        cn_label = tpl.get("scene_label", "")
        if any(ch in scene_lower for ch in cn_label):
            score += 2
        if cn_label and cn_label[:2] in scene_lower:
            score += 1
        if score > best_score:
            best_score = score
            best_match = key

    if best_match and best_match in _SPL_TEMPLATES:
        tpl = _SPL_TEMPLATES[best_match]
        spl = tpl["spl"]
        # 替换索引
        if index != "*":
            spl = spl.replace("index=*", f"index={index}")
        # 添加时间范围
        time_map = {"last_1h": "-1h@h", "last_4h": "-4h@h", "last_24h": "-1d@d",
                    "last_7d": "-7d@d", "last_30d": "-30d@d"}
        rt = time_map.get(time_range, "-1d@d")
        spl = f"{spl} | eval _time=now() | where _time > relative_time(now(), \"{rt}\")"

        return {
            "spl": spl,
            "scene_label": tpl["scene_label"],
            "note": f"匹配模板: {tpl['scene_label']} | 索引: {index} | 时间: {time_range}",
            "index": index,
            "time_range": time_range,
        }

    # 无匹配 → 生成通用查询
    spl_parts = []
    for word in search_scenario.split()[:5]:
        if len(word) > 2:
            spl_parts.append(word)
    if spl_parts:
        search_terms = " OR ".join(spl_parts)
        spl = f'index={index} "{search_terms}" | stats count by src_ip | sort -count | head 50'
    else:
        spl = f"index={index} | head 50"

    return {
        "spl": spl,
        "scene_label": "自定义查询",
        "note": f"未匹配到模板，基于描述关键词生成 | 索引: {index} | 时间: {time_range}",
        "index": index,
        "time_range": time_range,
    }


# ──────────────────────────────────────────────

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