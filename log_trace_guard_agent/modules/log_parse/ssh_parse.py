"""SSH 登录日志解析器 — 支持带/不带 Syslog 前缀两种格式"""

import re
from datetime import datetime

from modules.log_parse.base_parser import BaseParser, ParsedLogFields
from common.time_util import parse_log_time


class SSHParser(BaseParser):
    """SSH 登录日志解析器"""

    device_type = "ssh"

    PATTERNS = [
        # 完整格式: "Mar 15 10:30:25 server sshd[1234]: Accepted password for root from 192.168.1.1 port 22"
        re.compile(
            r"(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}).*sshd\[\d+\]:\s+Accepted\s+\w+\s+for\s+(\w+)\s+from\s+([\d.]+)\s+port\s+(\d+)",
            re.IGNORECASE,
        ),
        # 清洗后格式: "sshd[1234]: Accepted password for root from 192.168.1.1 port 22"
        re.compile(
            r"sshd\[\d+\]:\s+Accepted\s+\w+\s+for\s+(\w+)\s+from\s+([\d.]+)\s+port\s+(\d+)",
            re.IGNORECASE,
        ),
        # 完整格式 失败: "Mar 15 10:31:00 server sshd[1235]: Failed password for admin from 10.0.0.5 port 22"
        re.compile(
            r"(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}).*sshd\[\d+\]:\s+Failed\s+\w+\s+for\s+(\w+)\s+from\s+([\d.]+)\s+port\s+(\d+)",
            re.IGNORECASE,
        ),
        # 清洗后格式 失败: "sshd[1235]: Failed password for admin from 10.0.0.5 port 22"
        re.compile(
            r"sshd\[\d+\]:\s+Failed\s+\w+\s+for\s+(\w+)\s+from\s+([\d.]+)\s+port\s+(\d+)",
            re.IGNORECASE,
        ),
        # sudo 完整: "Mar 15 10:32:00 server sudo: root : TTY=pts/0 ; PWD=/home ; USER=root ; COMMAND=/bin/rm -rf /tmp"
        re.compile(
            r"(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}).*sudo:\s+(\w+)\s+.*COMMAND=(.+)$",
            re.IGNORECASE,
        ),
        # sudo 清洗后: "sudo: root : TTY=pts/0 ; PWD=/home ; USER=root ; COMMAND=/bin/rm -rf /tmp"
        re.compile(
            r"sudo:\s+(\w+)\s+.*COMMAND=(.+)$",
            re.IGNORECASE,
        ),
    ]

    def can_parse(self, log_line: str) -> bool:
        for pattern in self.PATTERNS:
            if pattern.search(log_line):
                return True
        return "sshd" in log_line.lower() or "sudo" in log_line.lower()

    def parse_fields(self, log_line: str) -> ParsedLogFields:
        result = ParsedLogFields(
            timestamp=parse_log_time(log_line),
            dst_port="22",
            device_type="ssh",
            raw_log=log_line[:500],
        )

        for pattern in self.PATTERNS:
            match = pattern.search(log_line)
            if not match:
                continue

            groups = match.groups()

            # 根据匹配组数判断格式
            if "Accepted" in log_line or "Failed" in log_line:
                if len(groups) == 4:
                    # 完整格式: timestamp, user, ip, port
                    result.timestamp = parse_log_time(match.group(1)) or result.timestamp
                    result.user = groups[1]
                    result.src_ip = groups[2]
                    result.src_port = groups[3]
                elif len(groups) == 3:
                    # 清洗后格式: user, ip, port
                    result.user = groups[0]
                    result.src_ip = groups[1]
                    result.src_port = groups[2]
                result.status = "success" if "Accepted" in log_line else "failed"
            elif "sudo" in log_line.lower():
                if len(groups) == 3:
                    # 完整格式: timestamp, user, command
                    result.timestamp = parse_log_time(match.group(1)) or result.timestamp
                    result.user = groups[1]
                    result.command = groups[2]
                elif len(groups) == 2:
                    # 清洗后格式: user, command
                    result.user = groups[0]
                    result.command = groups[1]
                result.status = "command_executed"

            break

        return self.validate(result)