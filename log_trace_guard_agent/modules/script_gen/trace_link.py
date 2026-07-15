"""模块四：攻击链路溯源策略 — 基于多源日志关键字段关联，梳理攻击链路"""

import re
from typing import Optional

from modules.script_gen.script_strategy import BaseScriptStrategy
from common.json_util import JsonConfigLoader
from app.settings import settings


class TraceLinkStrategy(BaseScriptStrategy):
    """攻击链路溯源策略 — 基于日志关联 + 攻击阶段判定"""

    strategy_type = "trace"
    strategy_name = "攻击链路溯源"

    # 攻击阶段链
    ATTACK_STAGES = [
        "侦查探测",
        "初始入侵",
        "权限提升",
        "横向移动",
        "持久化驻留",
        "数据窃取/破坏",
    ]

    # IP 关联场景
    ATTACK_PATTERNS = {
        "port_scan": re.compile(r"(?i)(scan|nmap|masscan|SYN|port.*probe)"),
        "brute_force": re.compile(r"(?i)(failed password|invalid user|login failed|authentication failure)"),
        "sql_injection": re.compile(r"(?i)(union.*select|select.*from|1=1|'|--\s|%27)"),
        "xss": re.compile(r"(?i)(<script|<img|onerror|alert\(|%3Cscript)"),
        "webshell": re.compile(r"(?i)(webshell|cmd=|exec=|passthru|system\()"),
        "data_exfil": re.compile(r"(?i)(select.*into outfile|dump|export|curl.*-d|wget.*-O)"),
        "lateral_move": re.compile(r"(?i)(psexec|wmiexec|smbexec|3389|rdp|ssh.*from.*to)"),
    }

    # 风险等级判断
    HIGH_RISK_EVENTS = ["sql_injection", "webshell", "data_exfil", "lateral_move"]
    MEDIUM_RISK_EVENTS = ["brute_force", "xss"]
    LOW_RISK_EVENTS = ["port_scan"]

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

        # 5. 生成总结
        summary = self._generate_summary(events, entry_point, attack_stage, attack_type)

        return {
            "attack_chain": events,
            "entry_point": entry_point or "未识别到明确攻击入口",
            "affected_assets": list(affected_assets) if affected_assets else ["未识别到受影响资产"],
            "attack_stage": attack_stage,
            "summary": summary,
        }

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
        for atype, pattern in self.ATTACK_PATTERNS.items():
            if pattern.search(log_lower):
                event_type = atype
                break

        # 风险等级
        if event_type in self.HIGH_RISK_EVENTS:
            risk_level = "high"
        elif event_type in self.MEDIUM_RISK_EVENTS:
            risk_level = "medium"
        elif event_type in self.LOW_RISK_EVENTS:
            risk_level = "low"
        else:
            risk_level = "info"

        # 动作描述
        action = self._describe_action(event_type, log_line)

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

    def _describe_action(self, event_type: str, log_line: str) -> str:
        """生成事件行为描述"""
        descriptions = {
            "port_scan": "端口扫描探测",
            "brute_force": "爆破攻击尝试",
            "sql_injection": "SQL注入攻击",
            "xss": "XSS跨站脚本攻击",
            "webshell": "Webshell上传/执行",
            "data_exfil": "数据泄露行为",
            "lateral_move": "横向移动尝试",
        }
        return descriptions.get(event_type, f"异常行为: {log_line[:80]}")

    def _identify_entry_point(self, events: list, logs: list) -> Optional[str]:
        """识别攻击入口 IP"""
        # 取第一个出现的 source IP 作为入口
        for event in events:
            if event.get("source"):
                return event["source"]
        return None

    def _identify_attack_stage(self, events: list) -> str:
        """判定攻击阶段"""
        if not events:
            return "未检测到攻击行为"

        has_high = any(e.get("risk_level") == "high" for e in events)
        has_medium = any(e.get("risk_level") == "medium" for e in events)
        has_lateral = any(e.get("event_type") == "lateral_move" for e in events)
        has_exfil = any(e.get("event_type") == "data_exfil" for e in events)

        if has_exfil:
            return "数据窃取/破坏"
        elif has_lateral:
            return "横向移动"
        elif has_high:
            return "权限提升/入侵"
        elif has_medium:
            return "初始入侵"
        elif has_medium:
            return "侦查探测"
        return "未检测到攻击行为"

    def _generate_summary(self, events: list, entry_point: Optional[str], stage: str, attack_type: Optional[str]) -> str:
        """生成溯源总结"""
        if not events:
            return "未检测到攻击行为，日志中无已知攻击特征。"

        total = len(events)
        high_count = sum(1 for e in events if e.get("risk_level") == "high")
        medium_count = sum(1 for e in events if e.get("risk_level") == "medium")

        summary = (
            f"溯源分析发现 **{total}** 条异常事件（高危 {high_count}，中危 {medium_count}），"
            f"攻击阶段判定为 **{stage}**。"
        )
        if entry_point:
            summary += f" 攻击入口: {entry_point}。"
        if attack_type:
            summary += f" 已知攻击类型: {attack_type}。"

        summary += " 建议对高危事件进行人工复核，并排查受影响资产的安全状态。"

        return summary