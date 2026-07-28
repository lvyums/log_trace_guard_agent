"""
Module 6: Log Correlation — Joint Log Analysis across Multiple Sources

Two-stage analysis engine:
  Stage 1 (fast path): 本地正则关键词预筛，零 API 调用
  Stage 2 (enhanced):  关键词匹配不足时降级 LLM 语义分析

Attack chain rules loaded from correlation_patterns.json (16 security rules).

Backward compatible: also provides TimelineBuilder for interactive timeline display.
"""

import json
import logging
import os
import re
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

from log_guard.common.utils import JsonConfigLoader, LogManager, Result
from log_guard.modules.log_parse import LogParseService

logger = LogManager.get_logger("log_correlate")

# ---------------------------------------------------------------------------
# 辅助：正则关键词编译缓存
# ---------------------------------------------------------------------------
_keyword_cache: Dict[str, re.Pattern] = {}


def _get_keyword_re(keyword: str) -> Optional[re.Pattern]:
    """编译并缓存正则关键词。"""
    if keyword not in _keyword_cache:
        try:
            _keyword_cache[keyword] = re.compile(keyword, re.IGNORECASE)
        except re.error:
            logger.warning(f"无效的正则关键词: {keyword}")
            return None
    return _keyword_cache[keyword]


# ---------------------------------------------------------------------------
# AttackChain — 检测到的攻击链结果
# ---------------------------------------------------------------------------

@dataclass
class AttackChain:
    """检测到的攻击链。"""
    chain_id: str = ""
    chain_name: str = ""
    description: str = ""
    risk_level: str = "P3_低风险"
    confidence: float = 0.0
    matched_keywords: List[str] = field(default_factory=list)
    matched_line_indices: List[int] = field(default_factory=list)
    matched_stages: List[str] = field(default_factory=list)
    indicators: List[str] = field(default_factory=list)
    suggestion: str = ""
    entity_key: str = ""
    matched_events: List[Any] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chain_id": self.chain_id or self.chain_name,
            "chain_name": self.chain_name,
            "description": self.description,
            "risk_level": self.risk_level,
            "confidence": round(self.confidence, 4),
            "matched_keywords": self.matched_keywords[:10],
            "matched_line_indices": self.matched_line_indices[:20],
            "matched_stages": self.matched_stages,
            "event_count": len(self.matched_line_indices),
            "indicators": self.indicators[:10],
            "suggestion": self.suggestion,
            "entity_key": self.entity_key,
        }

    def to_dict_detailed(self) -> Dict[str, Any]:
        d = self.to_dict()
        d["events"] = [e.to_dict() if hasattr(e, 'to_dict') else str(e) for e in self.matched_events[:50]]
        return d


# ---------------------------------------------------------------------------
# AttackChainMatcher — 纯正则关键词匹配（Stage 1）
# ---------------------------------------------------------------------------

class AttackChainMatcher:
    """基于关键词的攻击链匹配器。零外部调用，纯本地 regex。"""

    _SEVERITY_MAP = {
        "critical": "P0_高危",
        "major": "P1_中危",
        "warning": "P2_低危",
    }

    def __init__(self):
        self._rules: List[dict] = []
        self._load_rules()

    def _load_rules(self):
        try:
            data = JsonConfigLoader.load("correlation_patterns.json")
            self._rules = data.get("rules", []) if data else []
        except (FileNotFoundError, ValueError, Exception) as e:
            logger.warning(f"加载 correlation_patterns.json 失败: {e}")
            self._rules = []

    @property
    def patterns(self) -> List[dict]:
        return list(self._rules)

    def match(self, log_lines: List[str]) -> List[AttackChain]:
        """对日志行执行快速关键词匹配，返回匹配的攻击链。"""
        if not self._rules or not log_lines:
            return []

        results: List[AttackChain] = []

        for rule in self._rules:
            chain = self._match_rule(rule, log_lines)
            if chain is not None:
                results.append(chain)

        results.sort(key=lambda c: c.confidence, reverse=True)

        # 去重：same chain_name 保留最高置信度
        seen: Set[str] = set()
        deduped: List[AttackChain] = []
        for c in results:
            if c.chain_name not in seen:
                seen.add(c.chain_name)
                deduped.append(c)

        return deduped

    def _match_rule(self, rule: dict, log_lines: List[str]) -> Optional[AttackChain]:
        """针对一条规则，在所有日志行中匹配关键词模式。"""
        patterns = rule.get("patterns", [])
        if not patterns:
            return None

        rule_name = rule.get("name", "")
        severity = rule.get("severity", "warning")
        risk_level = self._SEVERITY_MAP.get(severity, "P3_低风险")
        required_matches = rule.get("required_matches", 2)
        min_freq = rule.get("min_freq", 1)

        matched_keywords: List[str] = []
        matched_lines: Set[int] = set()

        for pattern in patterns:
            keyword = pattern.get("keyword", "")
            source = pattern.get("source", ".*")

            keyword_re = _get_keyword_re(keyword)
            if keyword_re is None:
                continue

            source_re = _get_keyword_re(source) if source != ".*" else None

            pattern_matched_lines: List[int] = []
            for idx, line in enumerate(log_lines):
                if not keyword_re.search(line):
                    continue
                if source_re is not None and not source_re.search(line):
                    continue
                pattern_matched_lines.append(idx)

            if len(pattern_matched_lines) >= min_freq:
                matched_keywords.append(keyword)
                for li in pattern_matched_lines:
                    matched_lines.add(li)

        if len(matched_keywords) < required_matches:
            return None

        # 提取指标
        indicators = []
        for idx in sorted(matched_lines)[:20]:
            line = log_lines[idx]
            ips = re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', line)
            for ip in ips:
                if ip not in indicators:
                    indicators.append(f"IP: {ip}")
            users = re.findall(r'(?:user|用户)[=:]\s*(\S+)', line, re.IGNORECASE)
            for u in users:
                if f"用户: {u}" not in indicators:
                    indicators.append(f"用户: {u}")

        total_patterns = len(patterns)
        matched_pattern_count = len(matched_keywords)
        confidence = matched_pattern_count / total_patterns if total_patterns > 0 else 0.0

        # 只有一种关键词类型且出现次数很多 → 修正置信度
        if matched_pattern_count == 1 and len(matched_lines) >= min_freq * 5:
            confidence = min(0.6, confidence)

        suggestion = self._get_suggestion(rule, rule_name, severity)

        chain = AttackChain(
            chain_id=rule.get("id", rule_name),
            chain_name=rule_name,
            description=rule.get("description", ""),
            risk_level=risk_level,
            confidence=confidence,
            matched_keywords=matched_keywords,
            matched_line_indices=sorted(matched_lines),
            matched_stages=[f"阶段 {i+1}: {kw.split('|')[0][:30]}" for i, kw in enumerate(matched_keywords)],
            indicators=list(dict.fromkeys(indicators))[:10],
            suggestion=suggestion,
        )
        return chain

    @staticmethod
    def _get_suggestion(rule: dict, rule_name: str, severity: str) -> str:
        suggestions = {
            "ssh_brute_to_privesc": "立即封禁攻击源IP，检查被爆破的账户是否成功提权，修改密码并启用MFA。",
            "brute_force_attempt": "封禁攻击IP，检查是否有账户被成功登录，配置登录失败锁定策略和速率限制。",
            "sql_injection_chain": "检查Web应用是否存在SQL注入漏洞，查看数据库日志确认是否有数据泄露，阻断攻击IP。",
            "web_scan_to_exploit": "检查Web服务器访问日志确认是否存在成功入侵，修复漏洞，封禁扫描IP。",
            "initial_access_to_lateral": "立即隔离被入侵主机，检查内网横向移动范围和受感染的其他资产。",
            "privilege_escalation": "回滚提权操作，检查sudo配置和/etc/sudoers文件，重置受影响账户密码。",
            "data_exfiltration": "立即阻断异常出站流量，检查数据泄露范围，保留证据并启动应急响应流程。",
            "c2_beacon": "切断可疑外部通信，进行主机取证分析，确认是否存在木马/后门。",
            "ransomware_attack": "立即隔离受影响主机，断开网络连接，启动勒索软件应急响应流程，保留加密文件用于取证。",
            "internal_reconnaissance": "封禁内网扫描源，检查已发现的服务并修复已知漏洞，加强内网隔离。",
            "web_attack_to_data_theft": "阻断攻击IP，检查被利用的漏洞并修复，确认是否有用户数据泄露。",
            "dns_tunneling": "审查DNS日志，配置DNS过滤规则，阻断已知恶意域名。",
            "supply_chain_attack": "检查系统最近安装的第三方包，移除可疑组件，进行安全扫描和取证。",
            "insider_threat": "立即审查该用户的操作记录，回收异常权限，启动内部调查流程。",
            "waf_alert_to_attack": "检查WAF规则是否需要更新，对成功入侵路径进行溯源分析和应急响应。",
            "auth_failure_chain": "检查认证失败原因，确认账户是否被锁定，配置失败锁定的阈值和时长。",
        }
        for key, sug in suggestions.items():
            if key in rule_name:
                return sug
        if severity == "critical":
            return "立即排查并修复，防止进一步损失。"
        elif severity == "major":
            return "尽快排查，评估影响范围。"
        return "持续监控，必要时升级处理。"


# ---------------------------------------------------------------------------
# LLM 关联分析（Stage 2）— 同步版，适合 CLI 架构
# ---------------------------------------------------------------------------

def _parse_llm_json(text: str) -> Optional[list]:
    """
    从 LLM 返回的文本中恢复/解析攻击链 JSON 数组。
    处理截断、markdown 包裹、流式输出等异常情况。
    4 层容错策略。
    """
    if not text or not text.strip():
        return None

    text = text.strip()

    # Layer 1: 直接解析（完整 JSON）
    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass

    # Layer 2: 尝试补全缺失的数组/对象结束符
    clean = text.rstrip(",; \t\n\r")
    for suffix in ["]", "}]", "\n]", "\n}\n]"]:
        try:
            result = json.loads(clean + suffix)
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            continue

    # Layer 3: 提取第一个完整的 JSON 对象（流式/截断输出）
    try:
        decoder = json.JSONDecoder()
        idx = text.find("[")
        if idx >= 0:
            result, _ = decoder.raw_decode(text[idx:])
            if isinstance(result, list):
                return result
    except (json.JSONDecodeError, ValueError):
        pass

    # Layer 4: 按 } 分割，拼凑已完成的各个对象
    try:
        start = text.find("[")
        if start < 0:
            return None
        inner = text[start + 1:]
        objects_text = []
        depth = 0
        buf = ""
        for ch in inner:
            if ch == "{":
                depth += 1
                buf += ch
            elif ch == "}":
                depth -= 1
                buf += ch
                if depth == 0 and buf.strip():
                    objects_text.append(buf)
                    buf = ""
            elif depth > 0:
                buf += ch
        if objects_text:
            recovered = []
            for obj_str in objects_text:
                try:
                    obj = json.loads(obj_str)
                    if isinstance(obj, dict):
                        recovered.append(obj)
                except json.JSONDecodeError:
                    continue
            if recovered:
                return recovered
    except Exception:
        pass

    return None


class LLMChainAnalyzer:
    """大模型驱动的攻击链分析（同步版，适用于 CLI）。"""

    @classmethod
    def analyze(cls, log_lines: List[str]) -> dict:
        """调用 LLM 分析日志中的攻击链。"""
        if not log_lines:
            return {"chains": [], "summary": "没有日志可供分析"}

        try:
            from log_guard.ai_core.llm_client import get_llm
        except ImportError:
            logger.warning("无法加载 LLM 客户端，跳过 LLM 分析")
            return {"chains": [], "summary": "LLM 客户端不可用", "method": "llm_error"}

        # 构建日志行列表（带行号）
        log_text = "\n".join(f"[{i}] {line}" for i, line in enumerate(log_lines))

        system_prompt = """你是一个网络安全威胁狩猎专家。你的任务是从日志中**主动发现**攻击链证据，而不是保守地只报告"明确"的攻击。

已知攻击链候选（名称映射参考）：
1. ssh_brute_to_privesc — SSH 爆破 → 登录成功 → sudo 提权
2. ssh_brute_to_sudo_privesc — SSH 爆破 → sudo 执行敏感命令
3. sql_injection_to_data_exfil — SQL注入探测 → 数据提取 → 外传
4. web_scan_to_sql_injection — Web扫描 → SQL注入尝试
5. sql_injection_chain — SQL注入完整链（探测+利用+数据泄露）
6. waf_bypass_to_sql_injection — WAF绕过 → SQL注入
7. lateral_movement_via_ssh — SSH横向移动（内部IP互连）
8. c2_beacon_detected — C2通信特征（外连非常见端口）
9. data_exfil_via_dns — DNS隧道数据外传
10. ransomware_staging — 勒索软件准备阶段（加密+改名+外连）
11. supply_chain_attack — 供应链攻击（异常出站+可疑进程+第三方服务）
12. insider_threat — 内部威胁（非工作时间+大量下载+删除）
13. recon_to_exploit — 信息收集 → 漏洞利用链
14. multi_stage_web_attack — 多阶段Web攻击（扫描+注入+提权+外传）
15. dns_tunnel_to_c2 — DNS隧道 → C2通信
16. auth_failure_to_brute — 认证失败 → 暴力破解确认

输出 JSON 数组：
[
  {
    "chain_name": "攻击链名称（从上面选最匹配的，不限于上述列表）",
    "description": "简要描述攻击链",
    "risk_level": "P0_高危/P1_中危/P2_低危",
    "confidence": 0.0-1.0,
    "matched_line_indices": [行号数组],
    "matched_keywords": ["匹配到的关键词"],
    "indicators": ["关键指标，如IP地址、用户名等"],
    "suggestion": "处置建议"
  }
]

要求：
- **宽松判断**：只要日志中存在攻击链的至少2个阶段证据就应报告
- 单条日志如果同时体现多个阶段特征，也应报告
- 没有检测到任何攻击链时输出空数组 []
- risk_level: P0=高危需立即处理, P1=中危, P2=低危
- confidence: 0.3以上即可报告
- matched_line_indices 引用日志行号 [N]
- 输出必须是纯 JSON，不要用 markdown 包裹
- **务必确保 JSON 完整闭合**，不要中途截断输出"""

        user_input = f"以下日志共 {len(log_lines)} 行，请分析是否存在安全攻击链：\n\n{log_text}"

        try:
            llm = get_llm()
            result = llm.chat([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input},
            ], temperature=0.1, max_tokens=4096)

            if not result.get("success"):
                logger.warning(f"LLM 攻击链分析失败: {result.get('error', '未知错误')}")
                return {"chains": [], "summary": "LLM 分析失败", "method": "llm"}

            content = result["content"].strip()
            # 去掉可能的 markdown 包裹
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            chains = _parse_llm_json(content)
            if chains is None:
                logger.warning(f"LLM 返回无法恢复的 JSON: content={content[:300]}")
                return {"chains": [], "summary": "LLM 分析结果解析失败", "method": "llm"}

            return {"chains": chains, "summary": f"LLM 分析发现 {len(chains)} 条攻击链", "method": "llm"}

        except Exception as e:
            logger.warning(f"LLM 调用异常: {e}")
            return {"chains": [], "summary": "LLM 分析异常", "method": "llm"}


# ===================================================================
# 以下为向后兼容的 TimelineBuilder + ChainAnalyzer（用于交互式时间线显示）
# 新引擎使用上面的 AttackChainMatcher + LLMChainAnalyzer
# ===================================================================

# --- Timestamp parsing helpers (kept for backward compat) ---

_RE_ISO = re.compile(r"(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})")
_RE_SYSLOG = re.compile(r"(\w{3})\s+(\d{1,2})\s+(\d{2}):(\d{2}):(\d{2})")
_RE_WEB = re.compile(r"(\d{2})/(\w{3})/(\d{4}):(\d{2}):(\d{2}):(\d{2})")
_RE_ISO_FULL = re.compile(r"(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})")
_RE_SYSLOG_FRAC = re.compile(r"(\w{3})\s+(\d{1,2})\s+(\d{2}):(\d{2}):(\d{2})\.\d+")

_MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _parse_timestamp(ts_str: Optional[str]) -> Optional[datetime]:
    """Try to parse a timestamp string into a datetime object."""
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
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)),
                           int(m.group(4)), int(m.group(5)), int(m.group(6)))
        except (ValueError, TypeError):
            pass
    m = _RE_WEB.match(ts_str)
    if m:
        try:
            month = _MONTH_MAP.get(m.group(2).lower())
            if month:
                return datetime(int(m.group(3)), month, int(m.group(1)),
                               int(m.group(4)), int(m.group(5)), int(m.group(6)))
        except (ValueError, TypeError):
            pass
    m = _RE_SYSLOG_FRAC.match(ts_str)
    if m:
        try:
            month = _MONTH_MAP.get(m.group(1).lower())
            if month:
                return datetime(datetime.now().year, month, int(m.group(2)),
                               int(m.group(3)), int(m.group(4)), int(m.group(5)))
        except (ValueError, TypeError):
            pass
    m = _RE_SYSLOG.match(ts_str)
    if m:
        try:
            month = _MONTH_MAP.get(m.group(1).lower())
            if month:
                return datetime(datetime.now().year, month, int(m.group(2)),
                               int(m.group(3)), int(m.group(4)), int(m.group(5)))
        except (ValueError, TypeError):
            pass
    return None


# --- CorrelatedEvent (kept for backward compat timeline display) ---

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
        if self.src_ip:
            return self.src_ip
        if self.user:
            return self.user
        return self.device_type


# --- Old-style ChainAnalyzer (kept for backward compat, uses stages format) ---

class ChainAnalyzer:
    """Legacy analyzer for old-format patterns (stages-based).
    Kept for backward compatibility with TimelineBuilder.
    Uses the new correlation_patterns.json but with backward-compatible API.
    """

    def __init__(self):
        self._patterns: List[dict] = []
        self._load_patterns()

    def _load_patterns(self):
        try:
            data = JsonConfigLoader.load("correlation_patterns.json")
            self._patterns = data.get("rules", [])
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
        """Analyze timeline using new keyword-based pattern matching.
        This is a simplified version that delegates to AttackChainMatcher.
        """
        if not timeline:
            return []
        raw_lines = [e.raw_log for e in timeline if e.raw_log]
        matcher = AttackChainMatcher()
        return matcher.match(raw_lines)


# --- TimelineBuilder (kept for backward compat) ---

class TimelineBuilder:
    """Build a unified timeline from multiple log entries.
    Uses LogParseService for per-line parsing.
    """

    def __init__(self, time_window_minutes: int = 5):
        self._parse_svc = LogParseService()
        self.time_window_minutes = time_window_minutes

    def build_timeline(
        self,
        log_lines: List[str],
        source_label: str = "input",
    ) -> Tuple[List[CorrelatedEvent], Dict[str, List[CorrelatedEvent]]]:
        events: List[CorrelatedEvent] = []
        for i, line in enumerate(log_lines, 1):
            line = line.strip()
            if not line:
                continue
            if line.startswith("#") or line.startswith("──") or line.startswith("───"):
                continue
            parse_result = self._parse_svc.parse_log(line)
            parsed = parse_result if isinstance(parse_result, dict) else parse_result.get("data", {})
            risk_result = self._parse_svc.assess_risk(parsed)
            risk = risk_result if isinstance(risk_result, dict) else risk_result.get("data", {})
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
# LogCorrelateService — 高层 API（向后兼容 + 新引擎）
# ---------------------------------------------------------------------------

class LogCorrelateService:
    """日志联合审查服务。
    
    两级引擎：
      - keyword+LLM 混合分析（主要）
      - 时间线构建（向后兼容，detailed=True 时启用）
    """

    _matcher: Optional[AttackChainMatcher] = None

    @classmethod
    def _get_matcher(cls) -> AttackChainMatcher:
        if cls._matcher is None:
            cls._matcher = AttackChainMatcher()
        return cls._matcher

    @classmethod
    def correlate_logs(
        cls,
        log_lines: List[str],
        time_window_minutes: int = 5,
        use_llm: bool = False,
        detailed: bool = False,
    ) -> Dict[str, Any]:
        """
        两级引擎：关键词预筛 + 可选 LLM 增强（合并模式）。

        - use_llm=False: 关键词匹配优先 → 匹配到即返回 → 无匹配降级 LLM
        - use_llm=True: 关键词 + LLM 合并分析（双向保障）
        - detailed=True: 额外生成时间线（向后兼容，仅用于 CLI 菜单）
        """
        if not log_lines:
            return Result.ok({
                "total_events": 0,
                "device_types": [],
                "entities": [],
                "timeline": [],
                "chains": [],
                "summary": "没有日志可供分析",
                "method": "none",
                "matched_keywords": [],
            })

        lines = [l.strip() for l in log_lines if l.strip()]

        # Stage 1: 关键词快速匹配（总是执行）
        matcher = cls._get_matcher()
        keyword_chains = matcher.match(lines)

        # 用于 detailed=True 的时间线（向后兼容）
        detailed_timeline = []
        detailed_device_types = []
        detailed_entities = []
        if detailed:
            try:
                tb = TimelineBuilder(time_window_minutes=time_window_minutes)
                timeline, entity_groups = tb.build_timeline(lines)
                detailed_timeline = [e.to_dict() for e in timeline]
                detailed_device_types = sorted(set(e.device_type for e in timeline if e.device_type != "unknown"))
                detailed_entities = sorted(set(e.get_entity_key() for e in timeline))
            except Exception as e:
                logger.warning(f"构建时间线失败（非关键）: {e}")

        # Stage 2: 合并策略
        if not use_llm:
            # ── 纯关键词模式 ──
            if keyword_chains:
                high_risk = [c for c in keyword_chains if c.risk_level == "P0_高危"]
                chain_summary = f"关键词匹配到 {len(keyword_chains)} 条攻击链"
                if high_risk:
                    chain_summary += f"，其中 {len(high_risk)} 条高危"

                matched_kws = set()
                for c in keyword_chains:
                    for kw in c.matched_keywords:
                        matched_kws.add(kw.split("|")[0][:50])

                return Result.ok({
                    "total_events": len(lines),
                    "device_types": detailed_device_types or ["?"],
                    "entities": detailed_entities or ["?"],
                    "timeline": detailed_timeline,
                    "chains": [c.to_dict() for c in keyword_chains],
                    "summary": f"共分析 {len(lines)} 条日志。{chain_summary}。",
                    "method": "keyword",
                    "matched_keywords": sorted(matched_kws)[:20],
                })

            # 关键词无匹配 → 自动降级 LLM
            logger.info("关键词未匹配到攻击链，降级到 LLM 分析")
            llm_result = LLMChainAnalyzer.analyze(lines)
            return cls._normalize_llm_result(llm_result, len(lines), detailed_timeline,
                                              detailed_device_types, detailed_entities)
        else:
            # ── LLM 增强模式（关键词 + LLM 合并） ──
            llm_result = LLMChainAnalyzer.analyze(lines)
            llm_chains = llm_result.get("chains", [])

            if keyword_chains and not llm_chains:
                matched_kws = set()
                for c in keyword_chains:
                    for kw in c.matched_keywords:
                        matched_kws.add(kw.split("|")[0][:50])

                return Result.ok({
                    "total_events": len(lines),
                    "device_types": detailed_device_types or ["?"],
                    "entities": detailed_entities or ["?"],
                    "timeline": detailed_timeline,
                    "chains": [c.to_dict() for c in keyword_chains],
                    "summary": f"共分析 {len(lines)} 条日志。关键词匹配到 {len(keyword_chains)} 条攻击链（LLM 未检出）。",
                    "method": "keyword",
                    "matched_keywords": sorted(matched_kws)[:20],
                })

            if llm_chains and not keyword_chains:
                return cls._normalize_llm_result(llm_result, len(lines), detailed_timeline,
                                                  detailed_device_types, detailed_entities)

            if keyword_chains and llm_chains:
                # 两者都有 → 按 chain_name 去重合并
                chain_map: Dict[str, dict] = {}
                for kc in keyword_chains:
                    d = kc.to_dict()
                    d["_source"] = "keyword"
                    chain_map[d["chain_name"]] = d

                for lc in llm_chains:
                    name = lc.get("chain_name", "unknown")
                    if name in chain_map:
                        existing = chain_map[name]
                        existing["confidence"] = max(
                            float(existing.get("confidence", 0.5)),
                            float(lc.get("confidence", 0.5)),
                        )
                        if lc.get("description"):
                            existing["description"] = lc["description"]
                        if lc.get("indicators"):
                            existing_indicators = set(existing.get("indicators", []))
                            existing["indicators"] = list(existing_indicators | set(lc.get("indicators", [])))
                        if lc.get("suggestion"):
                            existing["suggestion"] = lc["suggestion"]
                    else:
                        lc["_source"] = "llm"
                        lc.setdefault("matched_keywords", ["LLM 语义分析发现"])
                        lc.setdefault("matched_line_indices", [])
                        lc.setdefault("event_count", 0)
                        chain_map[name] = lc

                merged = list(chain_map.values())
                kw_count = sum(1 for c in merged if c.get("_source") == "keyword")
                llm_count = sum(1 for c in merged if c.get("_source") == "llm")
                for c in merged:
                    c.pop("_source", None)

                matched_kws = set()
                for c in keyword_chains:
                    for kw in c.matched_keywords:
                        matched_kws.add(kw.split("|")[0][:50])

                return Result.ok({
                    "total_events": len(lines),
                    "device_types": detailed_device_types or ["?"],
                    "entities": detailed_entities or ["?"],
                    "timeline": detailed_timeline,
                    "chains": merged,
                    "summary": f"共分析 {len(lines)} 条日志。关键词+LLM 联合检出 {len(merged)} 条攻击链（关键词 {kw_count} 条 + LLM 补充 {llm_count} 条）。",
                    "method": "hybrid",
                    "matched_keywords": sorted(matched_kws)[:20],
                })

            # 两者都没有
            return Result.ok({
                "total_events": len(lines),
                "device_types": detailed_device_types or ["?"],
                "entities": detailed_entities or ["?"],
                "timeline": detailed_timeline,
                "chains": [],
                "summary": f"共分析 {len(lines)} 条日志。关键词与 LLM 均未检测到攻击链。",
                "method": "hybrid",
                "matched_keywords": [],
            })

    @classmethod
    def _normalize_llm_result(cls, llm_result: dict, total_lines: int,
                               detailed_timeline: list = None,
                               detailed_device_types: list = None,
                               detailed_entities: list = None) -> dict:
        """标准化 LLM 返回结果为统一格式。"""
        llm_chains = llm_result.get("chains", [])
        method = llm_result.get("method", "llm")

        if not llm_chains:
            return Result.ok({
                "total_events": total_lines,
                "device_types": detailed_device_types or ["?"],
                "entities": detailed_entities or ["?"],
                "timeline": detailed_timeline or [],
                "chains": [],
                "summary": f"共分析 {total_lines} 条日志。未检测到已知攻击链模式。",
                "method": method,
                "matched_keywords": [],
            })

        normalized = []
        for c in llm_chains:
            normalized.append({
                "chain_name": c.get("chain_name", "unknown"),
                "description": c.get("description", ""),
                "risk_level": c.get("risk_level", "P3_低风险"),
                "confidence": float(c.get("confidence", 0.5)),
                "matched_keywords": c.get("matched_keywords", []),
                "matched_line_indices": c.get("matched_line_indices", []),
                "event_count": len(c.get("matched_line_indices", [])),
                "indicators": c.get("indicators", []),
                "suggestion": c.get("suggestion", ""),
                "entity_key": c.get("entity_key", ""),
            })

        return Result.ok({
            "total_events": total_lines,
            "device_types": detailed_device_types or ["?"],
            "entities": detailed_entities or ["?"],
            "timeline": detailed_timeline or [],
            "chains": normalized,
            "summary": f"共分析 {total_lines} 条日志。LLM 分析发现 {len(normalized)} 条攻击链。",
            "method": method,
            "matched_keywords": [],
        })

    @classmethod
    def correlate_logs_from_file(
        cls,
        file_path: str,
        line_limit: int = 500,
        grep: Optional[str] = None,
        time_window_minutes: int = 5,
        detailed: bool = False,
        use_llm: bool = False,
        file_paths: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """从文件读取日志并执行联合审查。
        
        Args:
            file_path: Path to log file (single file).
            line_limit: Max lines to read.
            grep: Optional keyword filter.
            time_window_minutes: Time window for correlation.
            detailed: Include full event details.
            use_llm: Enable LLM enhanced analysis.
            file_paths: Optional multi-file path list.
        """
        from log_guard.core.log_reader import LogReader

        # 多文件模式
        if file_paths:
            parts: List[str] = []
            source_files: List[str] = []
            for fp in file_paths:
                try:
                    reader = LogReader()
                    result = reader.read_log(fp, line_limit=line_limit, grep=grep)
                    lines = result.get("lines", [])
                    if lines:
                        if len(file_paths) > 1:
                            parts.append(f"\n# ── 来源: {fp} ──\n" + "\n".join(lines))
                        else:
                            parts.extend(lines)
                        source_files.append(os.path.basename(fp))
                except Exception as e:
                    logger.warning(f"读取文件失败 {fp}: {e}，跳过")
            if not parts:
                return Result.ok({
                    "total_events": 0,
                    "device_types": [],
                    "entities": [],
                    "timeline": [],
                    "chains": [],
                    "summary": "没有可分析的日志",
                    "method": "none",
                    "matched_keywords": [],
                })
            if len(file_paths) > 1 and len(parts) > 1:
                combined = "\n".join(parts)
            else:
                combined = "\n".join(parts) if len(parts) > 1 else parts[0]
            lines = [l.strip() for l in combined.split("\n") if l.strip()]
            if len(lines) > 2000:
                lines = lines[-2000:]
        elif file_path:
            reader = LogReader()
            result = reader.read_log(file_path, line_limit=line_limit, grep=grep)
            lines = result.get("lines", [])
            source_files = [os.path.basename(file_path)]
        else:
            return Result.fail(msg="未指定文件路径")

        if not lines:
            return Result.ok({
                "total_events": 0,
                "device_types": [],
                "entities": [],
                "timeline": [],
                "chains": [],
                "summary": f"文件中没有匹配的日志行",
                "method": "none",
                "matched_keywords": [],
                "source_files": source_files if file_paths else [os.path.basename(file_path)],
            })

        correlation = cls.correlate_logs(
            log_lines=lines,
            time_window_minutes=time_window_minutes,
            use_llm=use_llm,
            detailed=detailed,
        )
        if isinstance(correlation, dict) and correlation.get("code") == 0:
            data = correlation["data"]
            data["source_files"] = source_files if file_paths else [os.path.basename(file_path)]
            data["file_total_lines"] = result.get("total_lines", 0) if not file_paths else len(lines)
        return correlation

    @property
    def available_patterns(self) -> List[dict]:
        """Return list of available attack chain patterns (for display)."""
        matcher = self._get_matcher()
        return [
            {
                "id": p.get("name"),
                "name": p.get("name"),
                "risk_level": AttackChainMatcher._SEVERITY_MAP.get(p.get("severity", ""), "P3_低风险"),
                "stages": [pp.get("keyword", "").split("|")[0][:40] for pp in p.get("patterns", [])],
                "description": p.get("description", ""),
            }
            for p in matcher.patterns
        ]
