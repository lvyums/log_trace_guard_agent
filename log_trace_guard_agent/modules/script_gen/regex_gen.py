"""模块四：正则规则生成策略 — 根据攻防场景自动生成行业标准正则"""

import re
from typing import Optional

from modules.script_gen.script_strategy import BaseScriptStrategy
from common.json_util import JsonConfigLoader
from app.settings import settings


class RegexGenStrategy(BaseScriptStrategy):
    """正则规则生成策略 — 基于规则知识库 + 场景模板"""

    strategy_type = "regex"
    strategy_name = "正则规则生成"

    # 攻击场景关键词 → 正则模板映射
    SCENE_KEYWORDS = {
        "ssh": ["ssh", "爆破", "brute", "登录", "login", "sshd"],
        "web": ["web", "http", "url", "get", "post", "sql注入", "xss", "扫描"],
        "sql": ["sql注入", "sqli", "database", "数据库", "mysql"],
        "port_scan": ["端口扫描", "scan", "nmap", "masscan", "探测"],
        "ddos": ["ddos", "dos", "拒绝服务", "flood", "攻击流量"],
        "malware": ["木马", "后门", "webshell", "trojan", "远控", "c2"],
        "privilege": ["提权", "权限提升", "sudo", "suid", "escalation"],
        "lateral": ["横向移动", "内网", "psexec", "wmiexec", "smbexec"],
    }

    def can_handle(self, params: dict) -> bool:
        scenario = (params.get("scenario") or "").lower()
        if not scenario:
            return False
        return True

    def generate(self, params: dict) -> dict:
        scenario = params.get("scenario", "")
        log_sample = params.get("log_sample")
        device_type = params.get("device_type")

        # 1. 识别攻击场景类型
        scene_type = self._identify_scene(scenario)

        # 2. 从外部配置加载规则模板
        config_path = f"{settings.rule_data_dir}/script_gen_regex.json"
        templates = JsonConfigLoader.load(config_path) or {}

        # 3. 匹配模板或生成规则
        regexes = []
        if scene_type in templates:
            for tpl in templates[scene_type]:
                rule = {
                    "name": tpl.get("name", ""),
                    "pattern": tpl.get("pattern", ""),
                    "description": tpl.get("description", ""),
                    "match_example": tpl.get("match_example"),
                    "priority": tpl.get("priority", 50),
                }
                regexes.append(rule)

        # 4. 基于日志样例微调（如有）
        if log_sample and regexes:
            for rule in regexes:
                if rule.get("match_example"):
                    pattern = rule["pattern"]
                    try:
                        if re.search(pattern, log_sample, re.IGNORECASE):
                            rule["match_example"] = log_sample[:200]
                    except re.error:
                        pass

        # 5. 兜底：无模板匹配时返回通用规则
        if not regexes:
            regexes = self._get_fallback_rules(scene_type, scenario)

        return {
            "regexes": regexes,
            "scenario": scenario,
            "note": self._get_note(regexes, scene_type),
        }

    def _identify_scene(self, scenario: str) -> str:
        """识别攻击场景类型"""
        scenario_lower = scenario.lower()
        scores = {}
        for scene_type, keywords in self.SCENE_KEYWORDS.items():
            score = sum(2 if kw in scenario_lower else 0 for kw in keywords)
            if score > 0:
                scores[scene_type] = score
        if scores:
            return max(scores, key=scores.get)
        return "unknown"

    def _get_fallback_rules(self, scene_type: str, scenario: str) -> list[dict]:
        """兜底规则生成"""
        fallbacks = {
            "ssh": [{
                "name": "SSH爆破检测",
                "pattern": r"(?i)(Failed password|Invalid user|authentication failure).*from\s+([\d.]+)",
                "description": "检测SSH登录失败（爆破攻击特征）",
                "match_example": "sshd[1234]: Failed password for root from 192.168.1.1 port 22",
                "priority": 80,
            }],
            "web": [{
                "name": "SQL注入检测",
                "pattern": r"(?i)(union.*select|select.*from|1=1|'|\"|--\s|%27|%22|%3D|%3B)",
                "description": "检测SQL注入攻击特征（联合查询/恒真条件/注释符）",
                "match_example": "GET /user?id=1' OR '1'='1 HTTP/1.1",
                "priority": 85,
            }],
            "sql": [{
                "name": "SQL注入检测",
                "pattern": r"(?i)(union.*select|select.*from|1=1|'|\"|--\s|%27|%22)",
                "description": "检测SQL注入攻击特征",
                "match_example": "SELECT * FROM users WHERE id=1' OR '1'='1",
                "priority": 85,
            }],
            "port_scan": [{
                "name": "端口扫描检测",
                "pattern": r"(?i)(scan|nmap|masscan|port.*scan|SYN scan|stealth scan)",
                "description": "检测端口扫描行为",
                "match_example": "SRC=192.168.1.100 DST=10.0.0.1 PROTO=TCP SPT=54321 DPT=22",
                "priority": 70,
            }],
        }
        return fallbacks.get(scene_type, [{
            "name": "通用规则",
            "pattern": rf"(?i){re.escape(scenario[:50])}",
            "description": f"基于场景「{scenario[:50]}」的通用检测规则",
            "match_example": None,
            "priority": 50,
        }])

    def _get_note(self, regexes: list, scene_type: str) -> Optional[str]:
        """生成附加说明"""
        if not regexes:
            return "未匹配到已知攻击场景，建议补充日志样例后重新生成。"
        if scene_type == "unknown":
            return "场景类型未明确识别，已生成通用规则，建议细化场景描述。"
        return None