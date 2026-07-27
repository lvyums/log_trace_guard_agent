"""
模块六：日志联合审查 — 日志联合审查引擎

从 JSON 规则（security attack chains）加载攻击链检测规则。
两级分析引擎：
  Stage 1 (fast path): 本地正则关键词预筛，零 API 调用
  Stage 2 (enhanced): 关键词匹配不足时降级 LLM 语义分析

去掉原来的逐行 parse_log + assess_risk（N 行 = 2N 次 LLM 调用）。
改为一次性的正则关键词匹配（毫秒级）+ 按需 LLM 降级。

联动其他模块：
  - /to-trace:  攻击链 → script-gen/trace 生成溯源 ES 查询
  - /to-scenario: 攻击链 → training/dispatch 生成实训场景
"""

import json
import os
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

from core.context_manager import ContextManager
from common.json_util import JsonConfigLoader
from common.logger import LogManager
from common.result_util import Result
from app.settings import settings

from modules.log_correlate.temporal import TemporalAnalyzer

logger = LogManager.get_logger()

CORRELATION_PATTERNS_PATH = os.path.join(settings.rule_data_dir, "correlation_patterns.json")

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
    chain_name: str = ""
    description: str = ""
    risk_level: str = "P3_低风险"
    confidence: float = 0.0
    matched_keywords: List[str] = field(default_factory=list)
    matched_line_indices: List[int] = field(default_factory=list)
    matched_stages: List[str] = field(default_factory=list)
    indicators: List[str] = field(default_factory=list)
    suggestion: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chain_name": self.chain_name,
            "description": self.description,
            "risk_level": self.risk_level,
            "confidence": round(self.confidence, 2),
            "matched_keywords": self.matched_keywords[:10],
            "matched_line_indices": self.matched_line_indices[:20],
            "matched_stages": self.matched_stages,
            "event_count": len(self.matched_line_indices),
            "indicators": self.indicators[:10],
            "suggestion": self.suggestion,
        }


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
            data = JsonConfigLoader.load(CORRELATION_PATTERNS_PATH)
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

        # 降序按置信度
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
            # 从日志行提取 IP
            ips = re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', line)
            for ip in ips:
                if ip not in indicators:
                    indicators.append(f"IP: {ip}")
            # 提取用户名
            users = re.findall(r'(?:user|用户)[=:]\s*(\S+)', line, re.IGNORECASE)
            for u in users:
                if f"用户: {u}" not in indicators:
                    indicators.append(f"用户: {u}")

        # 置信度 = matched patterns / total patterns
        total_patterns = len(patterns)
        matched_pattern_count = len(matched_keywords)
        confidence = matched_pattern_count / total_patterns

        # 只有一种关键词类型且出现次数很多 → 修正置信度
        if matched_pattern_count == 1 and len(matched_lines) >= min_freq * 5:
            confidence = min(0.6, confidence)  # 单一模式基数大 ≠ 攻击链

        suggestion = self._get_suggestion(rule, rule_name, severity)

        chain = AttackChain(
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
        """按规则生成处置建议。"""
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
# LLM 关联分析（Stage 2）
# ---------------------------------------------------------------------------

class LLMChainAnalyzer:
    """大模型驱动的攻击链分析。接受原始日志行列表，一次性调用 LLM。"""

    @staticmethod
    def _parse_llm_json(text: str) -> Optional[list]:
        """
        从 LLM 返回的文本中恢复/解析攻击链 JSON 数组。
        处理截断、markdown 包裹、流式输出等异常情况。
        """
        if not text or not text.strip():
            return None

        text = text.strip()

        # 1. 直接解析（完整 JSON）
        try:
            result = json.loads(text)
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

        # 2. 尝试补全缺失的数组/对象结束符
        clean = text.rstrip(",; \t\n\r")
        for suffix in ["]", "}]", "\n]", "\n}\n]"]:
            try:
                result = json.loads(clean + suffix)
                if isinstance(result, list):
                    return result
            except json.JSONDecodeError:
                continue

        # 3. 提取第一个完整的 JSON 对象（流式/截断输出）
        try:
            decoder = json.JSONDecoder()
            idx = text.find("[")
            if idx >= 0:
                result, _ = decoder.raw_decode(text[idx:])
                if isinstance(result, list):
                    return result
        except (json.JSONDecodeError, ValueError):
            pass

        # 4. 尝试按 } 分割，拼凑已完成的各个对象
        try:
            # 找到第一个 [
            start = text.find("[")
            if start < 0:
                return None
            inner = text[start + 1:]
            # 按 } 分割每个可能的对象块
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

    @classmethod
    async def analyze(cls, log_lines: List[str]) -> dict:
        """调用 LLM 分析日志中的攻击链。"""
        from core.ai_base.llm_factory import LLMFactory

        if not log_lines:
            return {"chains": [], "summary": "没有日志可供分析"}

        # 构建日志行列表（带行号，方便 LLM 引用）
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
- **宽松判断**：只要日志中存在攻击链的至少2个阶段证据就应报告，不要等所有阶段都齐全
- 单条日志如果同时体现多个阶段特征（如SQL注入尝试中已有数据泄露迹象），也应报告
- 没有检测到任何攻击链时输出空数组 []
- risk_level: P0=高危需立即处理, P1=中危, P2=低危
- confidence: 证据越充分越高，0.3以上即可报告
- matched_line_indices 引用日志行号 [N]
- 输出必须是纯 JSON，不要用 markdown 包裹
- **务必确保 JSON 完整闭合**，不要中途截断输出"""

        user_input = f"以下日志共 {len(log_lines)} 行，请分析是否存在安全攻击链：\n\n{log_text}"

        try:
            llm = await LLMFactory.get_light_llm()
            result = await llm.chat([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input},
            ], temperature=0.1, timeout=60)

            if not result.get("success"):
                logger.warning(f"LLM 攻击链分析失败: {result.get('error', '未知错误')}")
                return {"chains": [], "summary": "LLM 分析失败", "method": "llm"}

            content = result["content"].strip()
            # 去掉可能的 markdown 包裹
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            chains = cls._parse_llm_json(content)
            if chains is None:
                logger.warning(f"LLM 返回无法恢复的 JSON: content={content[:300]}")
                return {"chains": [], "summary": "LLM 分析结果解析失败", "method": "llm"}

            return {"chains": chains, "summary": f"LLM 分析发现 {len(chains)} 条攻击链", "method": "llm"}

        except json.JSONDecodeError as e:
            logger.warning(f"LLM 返回非 JSON: {e}, content={content[:200]}")
            return {"chains": [], "summary": "LLM 分析结果解析失败", "method": "llm"}
        except Exception as e:
            logger.warning(f"LLM 调用异常: {e}")
            return {"chains": [], "summary": "LLM 分析异常", "method": "llm"}


# ---------------------------------------------------------------------------
# LogCorrelateService — 高层 API
# ---------------------------------------------------------------------------

class LogCorrelateService:
    """日志联合审查服务。"""

    _matcher: Optional[AttackChainMatcher] = None

    @classmethod
    def _get_matcher(cls) -> AttackChainMatcher:
        if cls._matcher is None:
            cls._matcher = AttackChainMatcher()
        return cls._matcher

    @classmethod
    async def correlate_logs(
        cls,
        log_lines: List[str],
        time_window_minutes: int = 5,
        use_llm: bool = False,
        detailed: bool = False,
    ) -> dict:
        """
        两级引擎：关键词预筛 + 可选 LLM 增强（合并模式）。

        - use_llm=False: 关键词匹配优先 → 匹配到即返回 → 无匹配降级 LLM
        - use_llm=True: 关键词 + LLM 合并分析（双向保障，不再一个为空全空）
        """
        if not log_lines:
            return Result.ok({
                "total_events": 0,
                "chains": [],
                "summary": "没有日志可供分析",
                "method": "none",
                "matched_keywords": [],
            })

        # 过滤空行
        lines = [l.strip() for l in log_lines if l.strip()]

        # Stage 1: 关键词快速匹配（总是执行，无API成本）
        matcher = cls._get_matcher()
        keyword_chains = matcher.match(lines)

        # ★ 时序推理增强：对所有匹配到的攻击链执行时间轴分析
        keyword_chain_dicts: List[dict] = []
        if keyword_chains:
            keyword_chain_dicts = [c.to_dict() for c in keyword_chains]
            for chain_dict in keyword_chain_dicts:
                TemporalAnalyzer.analyze(chain_dict, lines)

        # Stage 2: 合并策略
        if not use_llm:
            # ── 纯关键词模式（原有行为） ──
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
                    "chains": keyword_chain_dicts,
                    "summary": f"共分析 {len(lines)} 条日志。{chain_summary}。",
                    "method": "keyword",
                    "matched_keywords": sorted(matched_kws)[:20],
                })

            # 关键词无匹配 → 自动降级 LLM
            logger.info("关键词未匹配到攻击链，降级到 LLM 分析")
            llm_result = await LLMChainAnalyzer.analyze(lines)
            return cls._normalize_llm_result(llm_result, len(lines))
        else:
            # ── LLM 增强模式（关键词 + LLM 合并） ──
            llm_result = await LLMChainAnalyzer.analyze(lines)
            llm_chains = llm_result.get("chains", [])

            if keyword_chains and not llm_chains:
                # LLM 没找到，但关键词找到了 → 返回关键词结果
                matched_kws_llm = sorted(set(
                    kw.split("|")[0][:50] for c in keyword_chain_dicts for kw in c.get("matched_keywords", [])
                ))[:20]
                return Result.ok({
                    "total_events": len(lines),
                    "chains": keyword_chain_dicts,
                    "summary": f"共分析 {len(lines)} 条日志。关键词匹配到 {len(keyword_chains)} 条攻击链（LLM 未检出）。",
                    "method": "keyword",
                    "matched_keywords": matched_kws_llm,
                })

            if llm_chains and not keyword_chains:
                # 关键词没找到，LLM 找到了
                return cls._normalize_llm_result(llm_result, len(lines))

            if keyword_chains and llm_chains:
                # 两者都有 → 按 chain_name 去重合并
                chain_map: Dict[str, dict] = {}
                for kcd in keyword_chain_dicts:
                    kcd["_source"] = "keyword"
                    chain_map[kcd["chain_name"]] = kcd

                for lc in llm_chains:
                    name = lc.get("chain_name", "unknown")
                    if name in chain_map:
                        # 关键词已有的链 → LLM 补充信息但不覆盖
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
                        # LLM 新发现的链
                        lc["_source"] = "llm"
                        lc.setdefault("matched_keywords", ["LLM 语义分析发现"])
                        lc.setdefault("matched_line_indices", [])
                        lc.setdefault("event_count", 0)
                        chain_map[name] = lc

                merged = list(chain_map.values())
                kw_count = sum(1 for c in merged if c.get("_source") == "keyword")
                llm_count = sum(1 for c in merged if c.get("_source") == "llm")

                # 移除内部标记
                for c in merged:
                    c.pop("_source", None)

                return Result.ok({
                    "total_events": len(lines),
                    "chains": merged,
                    "summary": f"共分析 {len(lines)} 条日志。关键词+LLM 联合检出 {len(merged)} 条攻击链（关键词 {kw_count} 条 + LLM 补充 {llm_count} 条）。",
                    "method": "hybrid",
                    "matched_keywords": sorted(set(
                        kw.split("|")[0][:50] for c in keyword_chain_dicts for kw in c.get("matched_keywords", [])
                    ))[:20],
                })

            # 两者都没有
            return Result.ok({
                "total_events": len(lines),
                "chains": [],
                "summary": f"共分析 {len(lines)} 条日志。关键词与 LLM 均未检测到攻击链。",
                "method": "hybrid",
                "matched_keywords": [],
            })

    @classmethod
    def _normalize_llm_result(cls, llm_result: dict, total_lines: int) -> dict:
        """标准化 LLM 返回结果为统一格式。"""
        llm_chains = llm_result.get("chains", [])
        method = llm_result.get("method", "llm")

        if not llm_chains:
            return Result.ok({
                "total_events": total_lines,
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
            })

        return Result.ok({
            "total_events": total_lines,
            "chains": normalized,
            "summary": f"共分析 {total_lines} 条日志。LLM 分析发现 {len(normalized)} 条攻击链。",
            "method": method,
            "matched_keywords": [],
        })

    @classmethod
    async def crunch_file(
        cls,
        file_path: Optional[str] = None,
        file_paths: Optional[list[str]] = None,
        file_content: Optional[str] = None,
        time_window_minutes: int = 5,
        use_llm: bool = False,
    ) -> dict:
        """从文件读取日志并执行联合审查。支持单文件（file_path）或多文件（file_paths）。"""
        content = file_content
        source_files: list[str] = []

        # 多文件路径 → 合并读取
        if file_paths and not content:
            parts: list[str] = []
            for fp in file_paths:
                try:
                    with open(fp, "r", encoding="utf-8", errors="replace") as f:
                        fc = f.read()
                    source_files.append(os.path.basename(fp))
                    if len(file_paths) > 1:
                        parts.append(f"\n# ── 来源: {fp} ──\n{fc}")
                    else:
                        parts.append(fc)
                except FileNotFoundError:
                    logger.warning(f"文件不存在: {fp}，跳过")
                except Exception as e:
                    logger.warning(f"读取文件失败 {fp}: {e}，跳过")
            if parts:
                content = "\n".join(parts)
                logger.info(f"已合并 {len(parts)} 个日志文件，共 {len(content.splitlines())} 行")

        # 单文件路径
        if file_path and not content:
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                source_files.append(os.path.basename(file_path))
            except FileNotFoundError:
                return Result.fail(msg=f"文件不存在: {file_path}")
            except PermissionError:
                return Result.fail(msg=f"无权限读取文件: {file_path}")
            except Exception as e:
                return Result.fail(msg=f"读取文件失败: {e}")

        if not content or not content.strip():
            return Result.ok({
                "total_events": 0,
                "chains": [],
                "summary": "文件内容为空",
                "method": "none",
                "matched_keywords": [],
                "source_files": source_files,
            })

        lines = content.split("\n")
        # 限制最大行数
        if len(lines) > 2000:
            logger.warning(f"文件行数过多 ({len(lines)})，截断至 2000 行")
            lines = lines[-2000:]  # 保留最近 2000 行

        result = await cls.correlate_logs(
            log_lines=lines,
            time_window_minutes=time_window_minutes,
            use_llm=use_llm,
            detailed=False,
        )
        # 添加文件来源信息
        if isinstance(result, dict) and result.get("code") == 0:
            result["data"]["source_files"] = source_files
        return result

    @classmethod
    async def to_trace_script(
        cls,
        log_lines: List[str],
        chain_name: str = "",
        attack_type: str = "unknown",
        pre_analyzed: Optional[dict] = None,
        context: Optional[ContextManager] = None,
    ) -> dict:
        """攻击链 → 攻击溯源脚本（调用 script-gen/trace）"""
        from modules.script_gen.service import ScriptGenService

        try:
            result = await ScriptGenService.trace_attack(
                logs=log_lines[:100],
                attack_type=attack_type or "unknown",
                pre_analyzed=pre_analyzed,
                context=context,
            )
            return result if isinstance(result, dict) else result.to_dict() if hasattr(result, 'to_dict') else {"code": 0, "data": str(result)}
        except Exception as e:
            logger.error(f"生成溯源脚本失败: {e}")
            return Result.fail(msg=f"生成溯源脚本失败: {e}")

    @classmethod
    async def to_training_scenario(
        cls,
        log_lines: List[str],
        chain_name: str = "",
        chain_description: str = "",
        chain_data: Optional[dict] = None,
        context: Optional[ContextManager] = None,
    ) -> dict:
        """攻击链 → 实训场景

        两种模式：
          - chain_data 存在 → 动态生成专属实战场景（LLM 根据攻击数据定制）
          - chain_data 不存在 → 传统模式，按分类下发预置场景
        """
        from modules.training.service import TrainingService

        # ── 模式1：动态生成实战场景 ──
        if chain_data:
            from modules.log_correlate.temporal import TemporalAnalyzer

            try:
                # LLM 根据攻击数据生成场景内容
                training_data = await TemporalAnalyzer.generate_training(chain_data, log_lines)
                if training_data.get("scenario") and training_data.get("tasks"):
                    scenario = training_data["scenario"]
                    tasks = training_data["tasks"]
                    standard_answers = training_data["standard_answers"]

                    # 注入到 TaskEngine
                    from modules.training.task_engine import TaskEngine
                    scenario_id = TaskEngine.inject_scenario(
                        scenario={
                            "name": scenario.get("name", f"实战溯源：{chain_name}"),
                            "description": scenario.get("description", chain_description),
                            "category": scenario.get("category", "实战"),
                            "difficulty": scenario.get("difficulty", "中级"),
                            "objectives": scenario.get("objectives", []),
                            "tasks": tasks,
                        },
                        standard_answers=standard_answers,
                    )

                    # 构建标准化的 dispatch 返回格式
                    dispatch_result = [{
                        "scenario": {
                            "scenario_id": scenario_id,
                            "name": scenario.get("name", ""),
                            "category": scenario.get("category", "实战"),
                            "difficulty": scenario.get("difficulty", "中级"),
                            "order": 0,
                            "description": scenario.get("description", ""),
                            "objectives": scenario.get("objectives", []),
                        },
                        "tasks": [{
                            "task_id": t.get("task_id"),
                            "order": t.get("order", i + 1),
                            "title": t.get("title", ""),
                            "description": t.get("description", ""),
                            "input_type": t.get("input_type", "text"),
                            "input_data": log_lines[:50],  # 传入实际日志作为输入
                            "submit_type": t.get("submit_type", "conclusion"),
                            "hint": t.get("hint"),
                        } for i, t in enumerate(tasks)],
                        "total_tasks": len(tasks),
                        "completed_tasks": 0,
                        "_dynamic": True,  # 前端可据此显示"实战场景"标签
                    }]

                    return Result.ok({
                        "scenarios": dispatch_result,
                        "total": 1,
                        "message": f"已生成实战场景：{scenario.get('name', '')}",
                    })
            except Exception as e:
                logger.warning(f"动态场景生成失败，降级到传统模式: {e}")

        # ── 模式2：传统模式（按分类下发预置场景） ──
        # 根据攻击链名称推断合适的分类
        category_map: Dict[str, str] = {
            "brute_force": "basic",
            "auth_failure": "basic",
            "ssh": "basic",
            "sql_injection": "web_attack",
            "web_scan": "web_attack",
            "waf": "web_attack",
            "data_exfil": "lateral_movement",
            "lateral": "lateral_movement",
            "c2": "lateral_movement",
            "ransomware": "lateral_movement",
            "supply_chain": "filtering",
            "insider": "compliance",
            "recon": "web_attack",
            "privesc": "lateral_movement",
            "dns_tunnel": "filtering",
        }
        category = "web_attack"
        for key, cat in category_map.items():
            if key in chain_name.lower():
                category = cat
                break

        try:
            result = await TrainingService.dispatch_tasks(
                scenario_id=None,
                category=category,
                context=context,
            )
            return result if isinstance(result, dict) else Result.ok({"msg": f"已下发 {category} 分类的实训任务"})
        except Exception as e:
            logger.error(f"生成实训场景失败: {e}")
            return Result.fail(msg=f"生成实训场景失败: {e}")

    @classmethod
    def get_available_patterns(cls) -> List[dict]:
        """返回可用攻击链模式列表。"""
        matcher = cls._get_matcher()
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
