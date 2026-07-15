"""模块四：攻击链路溯源策略 — 基于多源日志关键字段关联，梳理攻击链路"""

import re
from typing import Optional

from modules.script_gen.script_strategy import BaseScriptStrategy
from common.json_util import JsonConfigLoader
from common.logger import LogManager
from app.schemas.risk_level import RiskLevel
from app.settings import settings

logger = LogManager.get_logger()


class TraceLinkStrategy(BaseScriptStrategy):
    """攻击链路溯源策略 — 基于日志关联 + 攻击阶段判定 + RAG知识库增强"""

    strategy_type = "trace"
    strategy_name = "攻击链路溯源"

    def __init__(self):
        self._attack_stages = []
        self._attack_patterns = {}
        self._high_risk_events = []
        self._medium_risk_events = []
        self._low_risk_events = []
        self._event_descriptions = {}
        self._load_config()

    def _load_config(self):
        """加载外部配置"""
        config_path = f"{settings.rule_data_dir}/script_gen_trace_patterns.json"
        config = JsonConfigLoader.load(config_path) or {}

        self._attack_stages = config.get("attack_stages", [
            "侦查探测", "初始入侵", "权限提升", "横向移动",
            "持久化驻留", "数据窃取/破坏",
        ])

        raw_patterns = config.get("attack_patterns", {})
        self._attack_patterns = {}
        for atype, pattern_str in raw_patterns.items():
            try:
                self._attack_patterns[atype] = re.compile(pattern_str)
            except re.error as e:
                logger.warning(f"攻击模式正则编译失败 [{atype}]: {e}")
                self._attack_patterns[atype] = re.compile(r"(?i)nothing_to_match")

        risk_levels = config.get("risk_levels", {})
        self._high_risk_events = set(risk_levels.get("high", ["sql_injection", "webshell", "data_exfil", "lateral_move"]))
        self._medium_risk_events = set(risk_levels.get("medium", ["brute_force", "xss"]))
        self._low_risk_events = set(risk_levels.get("low", ["port_scan"]))

        self._event_descriptions = config.get("event_descriptions", {})

    def can_handle(self, params: dict) -> bool:
        return bool(params.get("logs"))

    def generate(self, params: dict) -> dict:
        logs = params.get("logs", [])
        attack_type = params.get("attack_type")

        # 1. 逐条分析日志，提取事件
        events = []
        all_ips = set()
        affected_assets = set()

        for log_line in logs:
            event = self._analyze_log_event(log_line)
            if event:
                events.append(event)
                if event.get("source"):
                    all_ips.add(event["source"])
                if event.get("target"):
                    all_ips.add(event["target"])
                    affected_assets.add(event["target"])

        # 2. 按时间排序
        events.sort(key=lambda e: e.get("timestamp") or "")

        # 3. 判定攻击入口
        entry_point = self._identify_entry_point(events, logs)

        # 4. 判定攻击阶段
        attack_stage = self._identify_attack_stage(events)

        # 5. 尝试 RAG 知识库增强总结
        summary = self._generate_summary(events, entry_point, attack_stage, attack_type)

        # 6. 尝试 RAG 补充攻击链路知识
        if not events:
            rag_events, rag_note = self._try_rag_trace(logs, attack_type)
            if rag_events:
                events = rag_events
                if not attack_stage or attack_stage == "未检测到攻击行为":
                    attack_stage = self._identify_attack_stage(events)
                summary = self._generate_summary(events, entry_point, attack_stage, attack_type)
                if summary:
                    summary += "（注：部分数据来自知识库检索，建议人工验证）"

        return {
            "attack_chain": events,
            "entry_point": entry_point or "未识别到明确攻击入口",
            "affected_assets": list(affected_assets) if affected_assets else ["未识别到受影响资产"],
            "attack_stage": attack_stage,
            "summary": summary,
        }

    def _try_rag_trace(self, logs: list, attack_type: Optional[str]) -> tuple[list, Optional[str]]:
        """尝试通过 RAG 知识库获取攻击链路信息"""
        try:
            from core.ai_base.rag_factory import RAGFactory

            query = attack_type or " ".join(logs)[:200]
            rag = RAGFactory.get_rag("scripts")
            if rag:
                results = rag.search(query=query, top_k=3)
                if results:
                    events = []
                    for r in results:
                        events.append({
                            "timestamp": None,
                            "event_type": r.get("title", "knowledge"),
                            "source": "知识库",
                            "target": None,
                            "action": r.get("description", r.get("content", "")[:100]),
                            "risk_level": RiskLevel.INFO.value,
                            "detail": r.get("content", "")[:200],
                        })
                    return events, "已检索知识库相关攻击链路信息"
        except Exception as e:
            logger.warning(f"溯源RAG检索失败: {e}")
        return [], None

    def _analyze_log_event(self, log_line: str) -> Optional[dict]:
        """分析单条日志，提取事件"""
        log_lower = log_line.lower()

        # 提取时间戳
        timestamp = self._extract_timestamp(log_line)

        # 提取 IP
        ips = re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", log_line)
        src_ip = ips[0] if len(ips) > 0 else None
        dst_ip = ips[1] if len(ips) > 1 else None

        # 识别攻击类型
        event_type = "unknown"
        for atype, pattern in self._attack_patterns.items():
            if pattern.search(log_lower):
                event_type = atype
                break

        # 风险等级 — 配置驱动
        if event_type in self._high_risk_events:
            risk_level = RiskLevel.HIGH.value
        elif event_type in self._medium_risk_events:
            risk_level = RiskLevel.MEDIUM.value
        elif event_type in self._low_risk_events:
            risk_level = RiskLevel.LOW.value
        else:
            risk_level = RiskLevel.INFO.value

        # 动作描述
        action = self._event_descriptions.get(event_type, f"异常行为: {log_line[:80]}")

        return {
            "timestamp": timestamp,
            "event_type": event_type,
            "source": src_ip,
            "target": dst_ip,
            "action": action,
            "risk_level": risk_level,
            "detail": log_line[:200],
        }

    def _extract_timestamp(self, log_line: str) -> Optional[str]:
        """提取时间戳"""
        patterns = [
            r"(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})",
            r"(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})",
            r"\[(\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2})",
        ]
        for p in patterns:
            m = re.search(p, log_line)
            if m:
                return m.group(1)
        return None

    def _identify_entry_point(self, events: list, logs: list) -> Optional[str]:
        """识别攻击入口 IP"""
        for event in events:
            if event.get("source"):
                return event["source"]
        return None

    def _identify_attack_stage(self, events: list) -> str:
        """判定攻击阶段 — 根据事件风险等级递增判断"""
        if not events:
            return "未检测到攻击行为"

        has_high = any(e.get("risk_level") == RiskLevel.HIGH.value for e in events)
        has_medium = any(e.get("risk_level") == RiskLevel.MEDIUM.value for e in events)
        has_low = any(e.get("risk_level") == RiskLevel.LOW.value for e in events)
        has_lateral = any(e.get("event_type") == "lateral_move" for e in events)
        has_exfil = any(e.get("event_type") == "data_exfil" for e in events)

        if has_exfil:
            return "数据窃取/破坏"
        if has_lateral:
            return "横向移动"
        if has_high:
            return "权限提升/入侵"
        if has_medium:
            return "初始入侵"
        if has_low:
            return "侦查探测"

        # 有事件但无风险等级标记
        return "可疑行为（待进一步分析）"

    def _generate_summary(self, events: list, entry_point: Optional[str], stage: str, attack_type: Optional[str]) -> str:
        """生成溯源总结"""
        if not events:
            return "未检测到攻击行为，日志中无已知攻击特征。"

        total = len(events)
        high_count = sum(1 for e in events if e.get("risk_level") == RiskLevel.HIGH.value)
        medium_count = sum(1 for e in events if e.get("risk_level") == RiskLevel.MEDIUM.value)

        summary = (
            f"溯源分析发现 {total} 条异常事件"
        )
        if high_count > 0 or medium_count > 0:
            summary += f"（高危 {high_count}，中危 {medium_count}）"
        summary += f"，攻击阶段判定为 {stage}。"
        if entry_point:
            summary += f" 攻击入口: {entry_point}。"
        if attack_type:
            summary += f" 已知攻击类型: {attack_type}。"

        summary += " 建议对高危事件进行人工复核，并排查受影响资产的安全状态。"
        return summary