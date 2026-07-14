"""防火墙流量日志解析器 — 支持 iptables / pf / 商用防火墙 Syslog 格式"""

import re
from datetime import datetime

from modules.log_parse.base_parser import BaseParser
from common.time_util import parse_log_time


class FirewallParser(BaseParser):
    """防火墙流量日志解析器"""

    device_type = "firewall"

    PATTERNS = [
        # iptables: "Oct 11 14:32:23 server kernel: [UFW BLOCK] IN=eth0 OUT= MAC=... SRC=192.168.1.100 DST=10.0.0.1 PROTO=TCP SPT=54321 DPT=22"
        re.compile(
            r"(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}).*?SRC=([\d.]+)\s+DST=([\d.]+).*?PROTO=(\w+).*?SPT=(\d+)\s+DPT=(\d+)",
            re.IGNORECASE,
        ),
        # iptables ACCEPT: "Oct 11 14:32:23 server kernel: ACCEPT IN=eth0 OUT= SRC=10.0.0.1 DST=192.168.1.1 PROTO=TCP SPT=80 DPT=54321"
        re.compile(
            r"(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}).*?(ACCEPT|DROP|REJECT).*?SRC=([\d.]+)\s+DST=([\d.]+).*?PROTO=(\w+)",
            re.IGNORECASE,
        ),
        # pf: "Oct 11 14:32:23 fw01 pf: block in on em0 from 192.168.1.100 to 10.0.0.1 proto tcp port 22"
        re.compile(
            r"(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+\S+\s+pf:.*?from\s+([\d.]+)\s+to\s+([\d.]+)\s+proto\s+(\w+)(?:\s+port\s+(\d+))?",
            re.IGNORECASE,
        ),
        # 商用防火墙 Syslog: "Oct 11 14:32:23 firewall01 DENY TCP 192.168.1.100:54321 -> 10.0.0.1:22"
        re.compile(
            r"(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+\S+\s+(DENY|ALLOW|BLOCK|DROP|ACCEPT)\s+(\w+)\s+([\d.]+):(\d+)\s*->\s*([\d.]+):(\d+)",
            re.IGNORECASE,
        ),
    ]

    def can_parse(self, log_line: str) -> bool:
        log_lower = log_line.lower()
        fw_keywords = ["ufw", "pf:", "firewall", "kernel:", "block", "deny", "accept", "reject"]
        if any(kw in log_lower for kw in fw_keywords):
            return True
        for pattern in self.PATTERNS:
            if pattern.search(log_line):
                return True
        return False

    def parse_fields(self, log_line: str) -> dict:
        result = {
            "timestamp": parse_log_time(log_line),
            "src_ip": None,
            "dst_ip": None,
            "src_port": None,
            "dst_port": None,
            "user": None,
            "url": None,
            "method": None,
            "command": None,
            "status": "unknown",
            "device_type": "firewall",
            "protocol": None,
            "action": None,
        }

        for pattern in self.PATTERNS:
            match = pattern.search(log_line)
            if not match:
                continue

            groups = match.groups()

            # 模式1: iptables BLOCK/DROP（含 SRC/DST/SPT/DPT）
            if len(groups) == 6 and "SRC=" in log_line:
                result["timestamp"] = parse_log_time(log_line) or groups[0]
                result["src_ip"] = groups[1]
                result["dst_ip"] = groups[2]
                result["protocol"] = groups[3]
                result["src_port"] = groups[4]
                result["dst_port"] = groups[5]
                result["action"] = "block"

            # 模式2: iptables ACCEPT（含动作关键字）
            elif len(groups) == 5 and groups[1] in ("ACCEPT", "DROP", "REJECT"):
                result["timestamp"] = parse_log_time(log_line) or groups[0]
                result["action"] = groups[1].lower()
                result["src_ip"] = groups[2]
                result["dst_ip"] = groups[3]
                result["protocol"] = groups[4]

            # 模式3: pf 格式
            elif len(groups) == 5 and "pf:" in log_line:
                result["timestamp"] = parse_log_time(log_line) or groups[0]
                result["action"] = "block"  # pf 默认 action
                result["src_ip"] = groups[1]
                result["dst_ip"] = groups[2]
                result["protocol"] = groups[3]
                result["dst_port"] = groups[4]

            # 模式4: 商用防火墙 Syslog
            elif len(groups) == 7 and "->" in log_line:
                result["timestamp"] = parse_log_time(log_line) or groups[0]
                result["action"] = groups[1].lower()
                result["protocol"] = groups[2]
                result["src_ip"] = groups[3]
                result["src_port"] = groups[4]
                result["dst_ip"] = groups[5]
                result["dst_port"] = groups[6]

            break

        # 统一状态映射
        action = result.get("action", "")
        if action in ("block", "drop", "deny", "reject"):
            result["status"] = "blocked"
        elif action in ("accept", "pass", "allow"):
            result["status"] = "allowed"
        else:
            result["status"] = "unknown"

        return self.validate(result)
