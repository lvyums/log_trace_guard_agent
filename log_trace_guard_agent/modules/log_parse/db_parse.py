"""数据库审计日志解析器 — 支持 MySQL / PostgreSQL / SQL Server 审计格式"""

import re
from datetime import datetime

from modules.log_parse.base_parser import BaseParser
from common.time_util import parse_log_time


class DBParser(BaseParser):
    """数据库审计日志解析器"""

    device_type = "db"

    PATTERNS = [
        # MySQL general_log: "2023-10-11T14:32:23.000000+08:00  12 Query SELECT * FROM users WHERE id=1"
        re.compile(
            r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[+-]\d{2}:\d{2})?)\s+(\d+)\s+(Connect|Query|Quit|Execute)\s*(.*)",
            re.IGNORECASE,
        ),
        # MySQL slow_log: "# Time: 2023-10-11T14:32:23.000000+08:00\n# User@Host: root[root] @ [192.168.1.1]"
        re.compile(
            r"# Time:\s*(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}).*?# User@Host:\s*(\S+).*?\[(\d[\d.]+)\]",
            re.DOTALL | re.IGNORECASE,
        ),
        # PostgreSQL log: "2023-10-11 14:32:23.000 CST [12345] LOG:  connection received: host=192.168.1.1 user=admin"
        re.compile(
            r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s+\S+\s+\[\d+\]\s+(LOG|ERROR|WARNING|FATAL|INFO):\s+(.*)",
            re.IGNORECASE,
        ),
        # SQL Server Audit: "2023-10-11 14:32:23.123 [Server] Login failed for user 'admin'. Client IP: 192.168.1.1"
        re.compile(
            r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+)\s+\[(\S+)\]\s+(.*?)(?:\s+Client IP:\s*([\d.]+))?",
            re.IGNORECASE,
        ),
        # 通用审计格式: "2023-10-11 14:32:23 | DB | 192.168.1.1 | root | SELECT | 0 | success"
        re.compile(
            r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s*\|\s*\S+\s*\|\s*([\d.]+)\s*\|\s*(\S+)\s*\|\s*(\w+)\s*\|\s*(\d+)\s*\|\s*(\w+)",
            re.IGNORECASE,
        ),
    ]

    # SQL 危险操作关键词
    DANGEROUS_SQL_KEYWORDS = [
        "drop", "truncate", "delete", "update", "insert", "grant", "revoke",
        "alter", "create user", "drop user", "set password", "into outfile",
        "load_file", "into dumpfile", "information_schema", "mysql.user",
    ]

    def can_parse(self, log_line: str) -> bool:
        log_lower = log_line.lower()
        db_keywords = [
            "mysql", "postgresql", "postgres", "sqlserver", "mssql",
            "select", "insert", "update", "delete", "drop", "truncate",
            "query", "connection received", "login failed", "general_log",
            "slow_log", "audit",
        ]
        if any(kw in log_lower for kw in db_keywords):
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
            "dst_port": "3306",
            "user": None,
            "url": None,
            "method": None,
            "command": None,
            "status": "unknown",
            "device_type": "db",
            "sql_statement": None,
            "db_name": None,
            "is_dangerous": False,
        }

        for pattern in self.PATTERNS:
            match = pattern.search(log_line)
            if not match:
                continue

            groups = match.groups()

            # 模式1: MySQL general_log
            if len(groups) == 4 and groups[2] in ("Connect", "Query", "Quit", "Execute"):
                result["timestamp"] = parse_log_time(log_line) or groups[0]
                operation = groups[2].lower()
                content = groups[3].strip()

                if operation == "connect":
                    # 尝试提取用户（格式: root@localhost on mydb）
                    user_match = re.search(r"(\S+)@", content)
                    if user_match:
                        result["user"] = user_match.group(1)
                    else:
                        user_match = re.search(r"(\S+)\s+on", content)
                        if user_match:
                            result["user"] = user_match.group(1)
                elif operation in ("query", "execute"):
                    result["sql_statement"] = content
                    result["command"] = content[:200]
                    result["method"] = operation.upper()
                    result["is_dangerous"] = self._check_dangerous(content)

            # 模式2: MySQL slow_log
            elif len(groups) == 3 and "User@Host" in log_line:
                result["timestamp"] = parse_log_time(log_line) or groups[0]
                result["user"] = groups[1]
                result["src_ip"] = groups[2]

            # 模式3: PostgreSQL log
            elif len(groups) == 3 and groups[1] in ("LOG", "ERROR", "WARNING", "FATAL", "INFO"):
                result["timestamp"] = parse_log_time(log_line) or groups[0]
                log_level = groups[1].upper()
                content = groups[2]

                # 提取连接信息
                host_match = re.search(r"host=([\d.]+)", content)
                user_match = re.search(r"user=(\S+)", content)
                if host_match:
                    result["src_ip"] = host_match.group(1)
                if user_match:
                    result["user"] = user_match.group(1)

                # 提取 SQL
                sql_match = re.search(r"statement:\s*(.*)", content, re.IGNORECASE)
                if sql_match:
                    result["sql_statement"] = sql_match.group(1).strip()
                    result["command"] = result["sql_statement"][:200]
                    result["is_dangerous"] = self._check_dangerous(result["sql_statement"])

                if log_level in ("ERROR", "FATAL"):
                    result["status"] = "error"

            # 模式4: SQL Server Audit
            elif len(groups) == 4 and "[" in log_line:
                result["timestamp"] = parse_log_time(log_line) or groups[0]
                content = groups[2]
                if groups[3]:
                    result["src_ip"] = groups[3]

                # 提取用户
                user_match = re.search(r"for user '(\S+)'", content)
                if user_match:
                    result["user"] = user_match.group(1)

                if "login failed" in content.lower():
                    result["status"] = "failed"
                else:
                    result["status"] = "success"

            # 模式5: 通用审计格式
            elif len(groups) == 6 and "|" in log_line:
                result["timestamp"] = parse_log_time(log_line) or groups[0]
                result["src_ip"] = groups[1]
                result["user"] = groups[2]
                result["method"] = groups[3].upper()
                result["status"] = groups[5]
                result["is_dangerous"] = groups[3].upper() in ("DROP", "TRUNCATE", "DELETE", "UPDATE")

            break

        return self.validate(result)

    def _check_dangerous(self, sql: str) -> bool:
        """检查 SQL 是否包含危险操作"""
        sql_lower = sql.lower()
        return any(kw in sql_lower for kw in self.DANGEROUS_SQL_KEYWORDS)
