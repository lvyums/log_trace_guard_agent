"""WAF 攻击日志解析器 — 支持常见 WAF 格式（ModSecurity / 商用 WAF）"""

import re

from modules.log_parse.base_parser import BaseParser, ParsedLogFields
from common.time_util import parse_log_time


class WAFParser(BaseParser):
    """WAF 攻击日志解析器"""

    device_type = "waf"

    PATTERNS = [
        # ModSecurity: "[Wed Oct 11 14:32:23 2023] [error] ... Attack detected from 192.168.1.100"
        re.compile(
            r"\[([^\]]+)\]\s+\[error\].*?(?:attack|violation|blocked|denied).*?from\s+([\d.]+)",
            re.IGNORECASE,
        ),
        # 通用 WAF 格式: "2023-10-11 14:32:23 [WAF] BLOCKED 192.168.1.100 GET /wp-admin SQL_INJECTION"
        re.compile(
            r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+\[WAF\]\s+\w+\s+([\d.]+)\s+(\w+)\s+(\S+)\s+(\w+)",
            re.IGNORECASE,
        ),
        # JSON WAF 格式 (字段顺序灵活): 任意 JSON 包含 action + src_ip
        re.compile(
            r'"action"\s*:\s*"(BLOCK|block|DENY|deny|ALERT|alert|LOG|log)".*?"src_ip"\s*:\s*"([\d.]+)"',
            re.IGNORECASE,
        ),
        # JSON WAF 格式 (src_ip 在前): "src_ip" ... "action"
        re.compile(
            r'"src_ip"\s*:\s*"([\d.]+)".*?"action"\s*:\s*"(BLOCK|block|DENY|deny|ALERT|alert|LOG|log)"',
            re.IGNORECASE,
        ),
        # 商用 WAF Syslog: "Oct 11 14:32:23 waf01 WAF: Attack blocked src=192.168.1.100 dst=10.0.0.1 url=/login type=SQLi"
        re.compile(
            r"(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+\S+\s+WAF:.*?src=([\d.]+).*?url=(\S+).*?type=(\w+)",
            re.IGNORECASE,
        ),
    ]

    # 攻击类型关键词映射
    ATTACK_KEYWORDS = {
        "sqli": "SQL注入",
        "sql_injection": "SQL注入",
        "xss": "XSS跨站脚本",
        "cross-site": "XSS跨站脚本",
        "rce": "远程命令执行",
        "command_injection": "命令注入",
        "lfi": "本地文件包含",
        "rfi": "远程文件包含",
        "path_traversal": "路径穿越",
        "xxe": "XXE注入",
        "ssrf": "SSRF服务端请求伪造",
        "file_upload": "恶意文件上传",
        "scan": "扫描探测",
        "brute_force": "暴力破解",
    }

    def can_parse(self, log_line: str) -> bool:
        log_lower = log_line.lower()
        waf_keywords = ["waf", "blocked", "attack detected", "violation", "[error]"]
        if any(kw in log_lower for kw in waf_keywords):
            return True
        for pattern in self.PATTERNS:
            if pattern.search(log_line):
                return True
        return False

    def parse_fields(self, log_line: str) -> ParsedLogFields:
        result = ParsedLogFields(
            timestamp=parse_log_time(log_line),
            dst_port="80",
            status="blocked",
            device_type="waf",
            raw_log=log_line[:500],
        )

        for pattern in self.PATTERNS:
            match = pattern.search(log_line)
            if not match:
                continue

            groups = match.groups()

            # 模式1: ModSecurity 格式
            if len(groups) == 2 and "attack" in log_line.lower():
                result.timestamp = parse_log_time(log_line) or groups[0]
                result.src_ip = groups[1]

            # 模式2: 通用 WAF 格式
            elif len(groups) == 5:
                result.timestamp = parse_log_time(log_line) or groups[0]
                result.src_ip = groups[1]
                result.method = groups[2]
                result.url = groups[3]
                result.attack_type = self._classify_attack(groups[4])

            # 模式3/4: JSON WAF 格式 (action在前或src_ip在前)
            elif len(groups) == 2 and '"action"' in pattern.pattern:
                # groups 可能是 (action, src_ip) 或 (src_ip, action)
                if groups[0].upper() in ("BLOCK", "DENY", "ALERT", "LOG"):
                    result.attack_action = groups[0]
                    result.src_ip = groups[1]
                else:
                    result.src_ip = groups[0]
                    result.attack_action = groups[1]

            # 模式5: 商用 WAF Syslog
            elif len(groups) == 4:
                result.timestamp = parse_log_time(log_line) or groups[0]
                result.src_ip = groups[1]
                result.url = groups[2]
                result.attack_type = self._classify_attack(groups[3])

            break

        # 从日志内容补充攻击类型
        if not getattr(result, "attack_type", None):
            result.attack_type = self._extract_attack_from_content(log_line)

        return self.validate(result)

    def _classify_attack(self, raw_type: str) -> str:
        """将原始攻击类型关键词映射为中文"""
        raw_lower = raw_type.lower()
        for keyword, cn_name in self.ATTACK_KEYWORDS.items():
            if keyword in raw_lower:
                return cn_name
        return raw_type

    def _extract_attack_from_content(self, log_line: str) -> str:
        """从日志内容中提取攻击类型"""
        log_lower = log_line.lower()
        for keyword, cn_name in self.ATTACK_KEYWORDS.items():
            if keyword in log_lower:
                return cn_name
        return "未知攻击"