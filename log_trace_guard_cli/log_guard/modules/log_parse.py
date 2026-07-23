"""
Module 1: Log Parsing

Provides log parsing infrastructure including parsers for SSH, Web, WAF,
Firewall, and Database log types, a parser factory, and a high-level
LogParseService with risk assessment capabilities.
"""

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Type

from log_guard.common.utils import (
    JsonConfigLoader,
    LogManager,
    Result,
    extract_ip_from_str,
    clean_special_chars,
)

logger = LogManager.get_logger("log_parse")


# ---------------------------------------------------------------------------
# LogParseResult
# ---------------------------------------------------------------------------

@dataclass
class LogParseResult:
    """Structured result of parsing a single log line."""

    timestamp: Optional[str] = None
    src_ip: Optional[str] = None
    dst_ip: Optional[str] = None
    user: Optional[str] = None
    status: Optional[str] = None
    command: Optional[str] = None
    device_type: Optional[str] = None
    raw_log: str = ""
    extra_info: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dict, excluding None values."""
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}

    def to_dict_all(self) -> Dict[str, Any]:
        """Convert to a dict, including all fields."""
        return asdict(self)


# ---------------------------------------------------------------------------
# BaseParser
# ---------------------------------------------------------------------------

class BaseParser(ABC):
    """Abstract base parser for log lines."""

    device_type: str = "unknown"

    @abstractmethod
    def parse_fields(self, log_line: str) -> Dict[str, Any]:
        """
        Parse a log line and return extracted fields as a dict.
        Keys should match LogParseResult field names where applicable.
        """
        ...

    @abstractmethod
    def can_parse(self, log_line: str) -> bool:
        """Return True if this parser can handle the given log line."""
        ...

    def parse(self, log_line: str) -> Optional[LogParseResult]:
        """Parse a log line into a LogParseResult. Returns None if not parseable."""
        if not self.can_parse(log_line):
            return None
        fields = self.parse_fields(log_line)
        fields.setdefault("raw_log", log_line)
        fields.setdefault("device_type", self.device_type)
        # Only pass known fields to LogParseResult
        known = {k: v for k, v in fields.items() if k in LogParseResult.__dataclass_fields__}
        return LogParseResult(**known)


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _contains_any(text: str, keywords: List[str], case_sensitive: bool = False) -> bool:
    """Check if text contains any of the given keywords."""
    if case_sensitive:
        return any(kw in text for kw in keywords)
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in keywords)


def _extract_timestamp(text: str) -> Optional[str]:
    """Extract a timestamp from a log line using common patterns."""
    patterns = [
        r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?",
        r"\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}",  # Jan 15 10:30:00
        r"\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2}",  # 15/Jan/2024:10:30:00
    ]
    for pat in patterns:
        match = re.search(pat, text, re.IGNORECASE)
        if match:
            return match.group(0)
    return None


def _extract_ips(text: str) -> List[str]:
    """Extract all IPv4 addresses from a string."""
    pattern = r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"
    matches = re.findall(pattern, text)
    valid = []
    for ip in matches:
        parts = ip.split(".")
        if all(0 <= int(p) <= 255 for p in parts):
            valid.append(ip)
    return valid


def _extract_user(text: str) -> Optional[str]:
    """Extract a username from log text."""
    patterns = [
        r"(?:for|user)\s+(\w+)",
        r"user[=:]\s*(\w+)",
        r"as\s+(\w+)(?:\s|$)",
    ]
    for pat in patterns:
        match = re.search(pat, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def _extract_command(text: str) -> Optional[str]:
    """Extract a command from sudo logs or similar."""
    cmd_match = re.search(r"COMMAND[=:]\s*(.+?)$", text, re.IGNORECASE)
    if cmd_match:
        return cmd_match.group(1).strip()
    sudo_match = re.search(r"sudo[:\s]+(.+?)$", text, re.IGNORECASE)
    if sudo_match:
        return sudo_match.group(1).strip()[:200]
    return None


def _extract_status(text: str) -> Optional[str]:
    """Extract a status code or word from log text."""
    status_match = re.search(r'"\s+(\d{3})\s+', text)
    if status_match:
        return status_match.group(1)
    word_match = re.search(
        r"\b(failed|success|accepted|rejected|denied|allowed|error|blocked)\b",
        text, re.IGNORECASE,
    )
    if word_match:
        return word_match.group(1).lower()
    return None


def _extract_url(text: str) -> Optional[str]:
    """Extract a URL from web log text."""
    patterns = [
        r'"(?:GET|POST|PUT|DELETE|HEAD|PATCH|OPTIONS)\s+(\S+)\s+HTTP',
        r'"(\S+)\s+HTTP/',
    ]
    for pat in patterns:
        match = re.search(pat, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


# ---------------------------------------------------------------------------
# SSHParser
# ---------------------------------------------------------------------------

class SSHParser(BaseParser):
    """Parser for SSH (sshd / sudo) log lines."""

    device_type = "ssh"

    MATCH_KEYWORDS = ["sshd", "failed password", "accepted", "session opened",
                      "session closed", "sudo"]

    def can_parse(self, log_line: str) -> bool:
        return _contains_any(log_line, self.MATCH_KEYWORDS)

    def parse_fields(self, log_line: str) -> Dict[str, Any]:
        fields: Dict[str, Any] = {}

        fields["timestamp"] = _extract_timestamp(log_line)

        # Source IP — prefer "from <ip>" pattern
        from_match = re.search(r"from\s+([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)", log_line, re.IGNORECASE)
        if from_match:
            fields["src_ip"] = from_match.group(1)
        else:
            ips = _extract_ips(log_line)
            if ips:
                fields["src_ip"] = ips[0]

        # Destination IP — second IP if present
        ips = _extract_ips(log_line)
        if len(ips) > 1:
            fields["dst_ip"] = ips[1]

        # User
        user = _extract_user(log_line)
        user_match = re.search(r"for\s+(\w+)\s+from", log_line, re.IGNORECASE)
        if user_match:
            fields["user"] = user_match.group(1)
        elif user:
            fields["user"] = user

        # Status
        if re.search(r"Failed\s+password", log_line, re.IGNORECASE):
            fields["status"] = "failed"
        elif re.search(r"Accepted\s+password|Accepted\s+publickey", log_line, re.IGNORECASE):
            fields["status"] = "success"
        elif re.search(r"session\s+opened", log_line, re.IGNORECASE):
            fields["status"] = "session_opened"
        elif re.search(r"session\s+closed", log_line, re.IGNORECASE):
            fields["status"] = "session_closed"
        elif re.search(r"sudo", log_line, re.IGNORECASE):
            fields["status"] = "sudo"
        else:
            st = _extract_status(log_line)
            if st:
                fields["status"] = st

        # Command (for sudo logs)
        cmd = _extract_command(log_line)
        if cmd:
            fields["command"] = cmd

        # Extra info
        extra: Dict[str, Any] = {}
        port_match = re.search(r"port\s+(\d+)", log_line, re.IGNORECASE)
        if port_match:
            extra["port"] = port_match.group(1)
        fields["extra_info"] = extra

        return fields


# ---------------------------------------------------------------------------
# WebParser
# ---------------------------------------------------------------------------

class WebParser(BaseParser):
    """Parser for Web (HTTP) server log lines."""

    device_type = "web"

    MATCH_KEYWORDS = ["HTTP/1.", "GET /", "POST /", "Mozilla", " 200 ", " 404 ", " 500 "]

    def can_parse(self, log_line: str) -> bool:
        if re.search(r'"(?:GET|POST|PUT|DELETE|HEAD|PATCH|OPTIONS)\s+\S+\s+HTTP/', log_line):
            return True
        return _contains_any(log_line, self.MATCH_KEYWORDS)

    def parse_fields(self, log_line: str) -> Dict[str, Any]:
        fields: Dict[str, Any] = {}

        # Timestamp — try common web formats first
        ts_match = re.search(
            r"\[(\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2}(?:\s[+-]\d{4})?)\]", log_line
        )
        if ts_match:
            fields["timestamp"] = ts_match.group(1)
        else:
            fields["timestamp"] = _extract_timestamp(log_line)

        # Source IP — first IP
        ips = _extract_ips(log_line)
        if ips:
            fields["src_ip"] = ips[0]

        # URL / path
        url = _extract_url(log_line)
        if url:
            fields["command"] = url
            fields.setdefault("extra_info", {})["url"] = url

        # HTTP method
        method_match = re.search(r'"(\w+)\s+\S+\s+HTTP/', log_line)
        if method_match:
            fields.setdefault("extra_info", {})["http_method"] = method_match.group(1)

        # Status code
        status_match = re.search(r'"\s+(\d{3})\s+', log_line)
        if status_match:
            fields["status"] = status_match.group(1)

        # User
        user_match = re.search(r'-\s+(\w+)\s+\[', log_line)
        if user_match and user_match.group(1) != "-":
            fields["user"] = user_match.group(1)

        # User-Agent
        ua_match = re.search(r'"([^"]*Mozilla[^"]*)"', log_line, re.IGNORECASE)
        if ua_match:
            fields.setdefault("extra_info", {})["user_agent"] = ua_match.group(1)

        # Response size
        size_match = re.search(r'"\s+\d{3}\s+(\d+)(?:\s+|$)', log_line)
        if size_match:
            fields.setdefault("extra_info", {})["response_size"] = size_match.group(1)

        return fields


# ---------------------------------------------------------------------------
# WAFParser
# ---------------------------------------------------------------------------

class WAFParser(BaseParser):
    """Parser for Web Application Firewall (WAF) log lines."""

    device_type = "waf"

    MATCH_KEYWORDS = ["waf", "modsecurity", "blocked", "sql injection",
                      "xss", "alert"]

    def can_parse(self, log_line: str) -> bool:
        return _contains_any(log_line, self.MATCH_KEYWORDS)

    def parse_fields(self, log_line: str) -> Dict[str, Any]:
        fields: Dict[str, Any] = {}

        fields["timestamp"] = _extract_timestamp(log_line)

        ips = _extract_ips(log_line)
        if ips:
            fields["src_ip"] = ips[0]
        if len(ips) > 1:
            fields["dst_ip"] = ips[1]

        # Status / action
        if re.search(r"blocked", log_line, re.IGNORECASE):
            fields["status"] = "blocked"
        elif re.search(r"alert", log_line, re.IGNORECASE):
            fields["status"] = "alert"
        elif re.search(r"detected", log_line, re.IGNORECASE):
            fields["status"] = "detected"
        elif re.search(r"pass|allow", log_line, re.IGNORECASE):
            fields["status"] = "allowed"

        # Extra info
        extra: Dict[str, Any] = {}
        if re.search(r"SQL\s*[Ii]nj(ection)?", log_line):
            extra["attack_type"] = "SQL Injection"
        elif re.search(r"XSS|Cross[- ]?Site", log_line, re.IGNORECASE):
            extra["attack_type"] = "XSS"
        elif re.search(r"LFI|RFI|path traversal|\.\./", log_line, re.IGNORECASE):
            extra["attack_type"] = "Path Traversal"
        elif re.search(r"command\s+injection|cmd\s*=", log_line, re.IGNORECASE):
            extra["attack_type"] = "Command Injection"
        elif re.search(r"scan(ner)?|probe", log_line, re.IGNORECASE):
            extra["attack_type"] = "Scanning"

        rule_match = re.search(r"(?:rule|id)[:=]\s*(\d+)", log_line, re.IGNORECASE)
        if rule_match:
            extra["rule_id"] = rule_match.group(1)

        sev_match = re.search(r"(?:severity|level)[:=]\s*(\w+)", log_line, re.IGNORECASE)
        if sev_match:
            extra["severity"] = sev_match.group(1).lower()

        uri_match = re.search(r"(?:uri|url)[:=]\s*(\S+)", log_line, re.IGNORECASE)
        if uri_match:
            extra["uri"] = uri_match.group(1)

        payload_match = re.search(r"(?:payload|data|input)[:=]\s*(.{0,100})", log_line, re.IGNORECASE)
        if payload_match:
            extra["payload"] = payload_match.group(1).strip()[:100]

        fields["extra_info"] = extra
        return fields


# ---------------------------------------------------------------------------
# FirewallParser
# ---------------------------------------------------------------------------

class FirewallParser(BaseParser):
    """Parser for Firewall (iptables/netfilter) log lines."""

    device_type = "firewall"

    MATCH_KEYWORDS = ["drop", "in=", "out=", "src=", "dst=", "proto=", "reject"]

    def can_parse(self, log_line: str) -> bool:
        return _contains_any(log_line, self.MATCH_KEYWORDS)

    def parse_fields(self, log_line: str) -> Dict[str, Any]:
        fields: Dict[str, Any] = {}

        fields["timestamp"] = _extract_timestamp(log_line)

        src_match = re.search(r"SRC=([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)", log_line, re.IGNORECASE)
        if src_match:
            fields["src_ip"] = src_match.group(1)

        dst_match = re.search(r"DST=([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)", log_line, re.IGNORECASE)
        if dst_match:
            fields["dst_ip"] = dst_match.group(1)

        # Status / action
        if re.search(r"\bDROP\b", log_line, re.IGNORECASE):
            fields["status"] = "dropped"
        elif re.search(r"\bREJECT\b", log_line, re.IGNORECASE):
            fields["status"] = "rejected"
        elif re.search(r"\bACCEPT\b", log_line, re.IGNORECASE):
            fields["status"] = "accepted"
        elif re.search(r"\bDENY\b", log_line, re.IGNORECASE):
            fields["status"] = "denied"
        elif re.search(r"\bALLOW\b", log_line, re.IGNORECASE):
            fields["status"] = "allowed"

        # Extra info
        extra: Dict[str, Any] = {}
        proto_match = re.search(r"PROTO=(\w+)", log_line, re.IGNORECASE)
        if proto_match:
            extra["protocol"] = proto_match.group(1).upper()

        sport_match = re.search(r"SPT=(\d+)", log_line, re.IGNORECASE)
        if sport_match:
            extra["src_port"] = sport_match.group(1)

        dport_match = re.search(r"DPT=(\d+)", log_line, re.IGNORECASE)
        if dport_match:
            extra["dst_port"] = dport_match.group(1)

        in_match = re.search(r"IN=(\S+)", log_line)
        if in_match and in_match.group(1) != "":
            extra["in_interface"] = in_match.group(1)

        out_match = re.search(r"OUT=(\S+)", log_line)
        if out_match and out_match.group(1) != "":
            extra["out_interface"] = out_match.group(1)

        len_match = re.search(r"LEN=(\d+)", log_line, re.IGNORECASE)
        if len_match:
            extra["packet_length"] = len_match.group(1)

        flags_match = re.search(r"(?:TCP|FLAGS)[:=](\S+)", log_line, re.IGNORECASE)
        if flags_match:
            extra["tcp_flags"] = flags_match.group(1)

        fields["extra_info"] = extra
        return fields


# ---------------------------------------------------------------------------
# DBParser
# ---------------------------------------------------------------------------

class DBParser(BaseParser):
    """Parser for Database (MySQL / PostgreSQL / Oracle) log lines."""

    device_type = "db"

    MATCH_KEYWORDS = ["mysql", "postgres", "postgresql", "ora-", "ORA-",
                      "database", " sql"]

    def can_parse(self, log_line: str) -> bool:
        return _contains_any(log_line, self.MATCH_KEYWORDS)

    def parse_fields(self, log_line: str) -> Dict[str, Any]:
        fields: Dict[str, Any] = {}

        fields["timestamp"] = _extract_timestamp(log_line)

        ips = _extract_ips(log_line)
        if ips:
            fields["src_ip"] = ips[0]

        # User
        user = _extract_user(log_line)
        db_user_match = re.search(r"(?:user|username)[=:]\s*(\w+)", log_line, re.IGNORECASE)
        if db_user_match:
            fields["user"] = db_user_match.group(1)
        elif user:
            fields["user"] = user

        # Status
        if re.search(r"(?:error|failed|denied|rejected)", log_line, re.IGNORECASE):
            fields["status"] = "error"
        elif re.search(r"(?:connect|login|opened|start)", log_line, re.IGNORECASE):
            fields["status"] = "connect"
        elif re.search(r"(?:disconnect|close|quit|end)", log_line, re.IGNORECASE):
            fields["status"] = "disconnect"
        elif re.search(r"(?:query|select|insert|update|delete|alter|drop|create)", log_line, re.IGNORECASE):
            fields["status"] = "query"

        # Command (SQL query)
        sql_patterns = [
            r"(?:query|statement)[=:]\s*(.+?)$",
            r"(?:SQL|sql)[=:]\s*(.+?)$",
            r"'(SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE)\s.+?'",
        ]
        for pat in sql_patterns:
            sql_match = re.search(pat, log_line, re.IGNORECASE | re.DOTALL)
            if sql_match:
                cmd = sql_match.group(1).strip()[:500]
                fields["command"] = cmd
                break

        # Extra info
        extra: Dict[str, Any] = {}
        if re.search(r"mysql", log_line, re.IGNORECASE):
            extra["db_type"] = "MySQL"
        elif re.search(r"postgres(ql)?", log_line, re.IGNORECASE):
            extra["db_type"] = "PostgreSQL"
        elif re.search(r"ora-|ORA-|oracle", log_line, re.IGNORECASE):
            extra["db_type"] = "Oracle"
        elif re.search(r"mssql|sql server", log_line, re.IGNORECASE):
            extra["db_type"] = "MSSQL"

        db_match = re.search(r"(?:database|db)[=:]\s*(\w+)", log_line, re.IGNORECASE)
        if db_match:
            extra["database_name"] = db_match.group(1)

        err_match = re.search(r"(ORA-\d{5}|Error\s+\d+|SQLSTATE\[\w+\])", log_line, re.IGNORECASE)
        if err_match:
            extra["error_code"] = err_match.group(1)

        port_match = re.search(r"port[=:]\s*(\d+)", log_line, re.IGNORECASE)
        if port_match:
            extra["port"] = port_match.group(1)

        fields["extra_info"] = extra
        return fields


# ---------------------------------------------------------------------------
# GenericParser - 兜底解析器，处理未知格式日志
# ---------------------------------------------------------------------------

class GenericParser(BaseParser):
    """Generic parser that tries to extract common fields from any log line."""

    device_type = "generic"

    def can_parse(self, log_line: str) -> bool:
        # Always return True as a fallback parser
        return True

    def parse_fields(self, log_line: str) -> Dict[str, Any]:
        fields: Dict[str, Any] = {}

        # Timestamp
        fields["timestamp"] = _extract_timestamp(log_line)

        # IPs
        ips = _extract_ips(log_line)
        if ips:
            fields["src_ip"] = ips[0]
        if len(ips) > 1:
            fields["dst_ip"] = ips[1]

        # User
        user = _extract_user(log_line)
        if user:
            fields["user"] = user

        # Status
        status = _extract_status(log_line)
        if status:
            fields["status"] = status

        # Command
        cmd = _extract_command(log_line)
        if cmd:
            fields["command"] = cmd

        # Try to detect level/log type from common patterns
        extra: Dict[str, Any] = {}
        level_match = re.search(r"\b(DEBUG|INFO|WARN(?:ING)?|ERROR|FATAL|CRITICAL|TRACE)\b", log_line, re.IGNORECASE)
        if level_match:
            extra["log_level"] = level_match.group(1).upper()

        # Detect if it's an application log with brackets like [2026-07-16 20:44:14]
        bracket_ts = re.search(r"\[(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\]", log_line)
        if bracket_ts:
            fields["timestamp"] = bracket_ts.group(1)
            extra["log_format"] = "application"

        fields["extra_info"] = extra
        return fields


# ---------------------------------------------------------------------------
# LogParserFactory
# ---------------------------------------------------------------------------

class LogParserFactory:
    """
    Factory for selecting and instantiating log parsers.

    Maintains a registry of parser classes keyed by device type
    and aliases. The ``get_parser()`` method iterates through
    registered parsers and returns the first one whose
    ``can_parse()`` method returns True.
    """

    def __init__(self):
        self._parsers: Dict[str, Type[BaseParser]] = {}
        self._aliases: Dict[str, str] = {}
        self._parser_instances: Dict[str, BaseParser] = {}
        self._fallback_parser: Optional[Type[BaseParser]] = None

    def register(self, device_type: str, parser_cls: Type[BaseParser], *aliases: str) -> None:
        """
        Register a parser class for a given device type.

        Args:
            device_type: Canonical device type name.
            parser_cls: Parser class (subclass of BaseParser).
            *aliases: Optional alternative names for this parser.
        """
        self._parsers[device_type] = parser_cls
        self._aliases[device_type] = device_type
        for alias in aliases:
            self._aliases[alias] = device_type

    def register_fallback(self, parser_cls: Type[BaseParser]) -> None:
        """Register a fallback parser used when no other parser matches."""
        self._fallback_parser = parser_cls

    def get_parser(self, log_line: str) -> Optional[BaseParser]:
        """
        Return the first parser that can handle the given log line.

        Iterates through all registered parsers and returns the first
        one whose ``can_parse()`` returns True. Falls back to the
        registered fallback parser if no specific parser matches.

        Args:
            log_line: A raw log line string.

        Returns:
            A BaseParser instance or None if no parser matches.
        """
        for device_type in self._parsers:
            parser = self._get_or_create(device_type)
            if parser.can_parse(log_line):
                return parser
        # Use fallback parser if registered
        if self._fallback_parser:
            fallback_key = "__fallback__"
            if fallback_key not in self._parser_instances:
                self._parser_instances[fallback_key] = self._fallback_parser()
            return self._parser_instances[fallback_key]
        return None

    def get_parser_by_type(self, device_type: str) -> Optional[BaseParser]:
        """Get a parser by its device type name."""
        resolved = self._aliases.get(device_type, device_type)
        if resolved in self._parsers:
            return self._get_or_create(resolved)
        return None

    def _get_or_create(self, device_type: str) -> BaseParser:
        if device_type not in self._parser_instances:
            self._parser_instances[device_type] = self._parsers[device_type]()
        return self._parser_instances[device_type]

    def parse(self, log_line: str) -> Optional[Dict[str, Any]]:
        """
        Parse a log line by finding the appropriate parser.

        Args:
            log_line: A raw log line string.

        Returns:
            A dict of parsed fields, or None if no parser matched.
        """
        parser = self.get_parser(log_line)
        if parser is None:
            return None
        result = parser.parse(log_line)
        if result is None:
            return None
        return result.to_dict()

    @property
    def registered_types(self) -> List[str]:
        """Return list of registered device types."""
        return list(self._parsers.keys())

    @property
    def registered_aliases(self) -> Dict[str, str]:
        """Return alias -> device_type mapping."""
        return dict(self._aliases)


# ---------------------------------------------------------------------------
# Default parsers registration
# ---------------------------------------------------------------------------

_default_factory: Optional[LogParserFactory] = None


def _register_default_parsers() -> LogParserFactory:
    """Create the default factory and register all built-in parsers."""
    factory = LogParserFactory()
    factory.register("ssh", SSHParser, "sshd", "secure")
    factory.register("web", WebParser, "http", "apache", "nginx", "iis")
    factory.register("waf", WAFParser, "modsecurity", "web_application_firewall")
    factory.register("firewall", FirewallParser, "iptables", "netfilter", "fw")
    factory.register("db", DBParser, "database", "mysql", "postgresql", "oracle")
    factory.register_fallback(GenericParser)
    return factory


def get_default_factory() -> LogParserFactory:
    """Get or create the default parser factory with all built-in parsers."""
    global _default_factory
    if _default_factory is None:
        _default_factory = _register_default_parsers()
    return _default_factory


# Register at module level
_default_factory = _register_default_parsers()


# ---------------------------------------------------------------------------
# LogParseService
# ---------------------------------------------------------------------------

class LogParseService:
    """
    High-level service for log parsing, identification, and risk assessment.

    Provides the same business logic as the original FastAPI project,
    adapted for CLI usage.
    """

    def __init__(self, factory: Optional[LogParserFactory] = None):
        self.factory = factory or get_default_factory()

    # ------------------------------------------------------------------
    # identify_log_type
    # ------------------------------------------------------------------

    def identify_log_type(self, log_line: str) -> Dict[str, Any]:
        """
        Identify the type / device_type of a log line.

        Uses log_features.json for feature-based matching with
        weighted keyword scoring as the primary method. Falls back
        to parser can_parse() checks if feature matching yields
        low confidence.

        Returns:
            dict with keys: device_type, confidence, identify_reason
        """
        result = {
            "device_type": "unknown",
            "confidence": 0.0,
            "identify_reason": "No matching features or parsers",
        }

        if not log_line or not log_line.strip():
            return result

        log_lower = log_line.lower()

        # Phase 1: Feature-based matching from log_features.json
        try:
            features = JsonConfigLoader.load("log_features.json")
            best_type = "unknown"
            best_score = 0.0
            best_matches: List[str] = []

            for device_type, keywords_data in features.items():
                score = 0.0
                matches: List[str] = []
                for entry in keywords_data:
                    keyword = entry.get("keyword", "").lower()
                    weight = entry.get("weight", 0.5)
                    if keyword in log_lower:
                        score += weight
                        matches.append(keyword)

                if score > best_score:
                    best_score = score
                    best_type = device_type
                    best_matches = matches
                elif score == best_score and score > 0:
                    if len(matches) > len(best_matches):
                        best_type = device_type
                        best_matches = matches

            if best_score > 0:
                max_possible = sum(
                    entry.get("weight", 0.5) for entry in features.get(best_type, [])
                )
                confidence = min(best_score / max_possible, 1.0) if max_possible > 0 else 0.0
                confidence = max(confidence, 0.3)

                result["device_type"] = best_type
                result["confidence"] = round(confidence, 4)
                result["identify_reason"] = (
                    f"Feature match: {', '.join(best_matches[:5])} "
                    f"(score={best_score:.2f})"
                )

                if confidence >= 0.5:
                    return result

        except (FileNotFoundError, ValueError, Exception) as e:
            logger.debug(f"Could not load log_features.json: {e}")

        # Phase 2: Parser-based fallback
        parser = self.factory.get_parser(log_line)
        if parser is not None:
            parser_confidence = 0.6
            if result["confidence"] < parser_confidence:
                result["device_type"] = parser.device_type
                result["confidence"] = parser_confidence
                result["identify_reason"] = (
                    f"Parser match: {parser.__class__.__name__} ({parser.device_type})"
                )

        return result

    # ------------------------------------------------------------------
    # parse_log
    # ------------------------------------------------------------------

    def parse_log(self, log_line: str) -> Dict[str, Any]:
        """
        Parse a log line and return structured fields.

        First identifies the log type, then applies the appropriate
        parser for deep field extraction.

        Returns:
            Result.ok(data=parsed_fields) or Result.fail(...)
        """
        result: Dict[str, Any] = {
            "timestamp": None,
            "src_ip": None,
            "dst_ip": None,
            "user": None,
            "status": None,
            "command": None,
            "device_type": "unknown",
            "raw_log": log_line,
            "extra_info": {},
        }

        if not log_line or not log_line.strip():
            return Result.fail("Empty log line")

        # Identify type
        id_result = self.identify_log_type(log_line)
        result["device_type"] = id_result["device_type"]

        # Parse with matched parser
        parser = self.factory.get_parser(log_line)
        if parser is not None:
            parsed = parser.parse(log_line)
            if parsed:
                for key in ("timestamp", "src_ip", "dst_ip", "user", "status", "command"):
                    val = getattr(parsed, key, None)
                    if val is not None:
                        result[key] = val
                if parsed.extra_info:
                    result["extra_info"] = parsed.extra_info

        return Result.ok(data=result)

    # ------------------------------------------------------------------
    # assess_risk
    # ------------------------------------------------------------------

    def assess_risk(self, parsed_fields: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess risk level of parsed log fields using risk_rules.json.

        Evaluates each risk rule against the parsed fields and returns
        the highest risk match found.

        Args:
            parsed_fields: Dict of parsed log fields (e.g. from parse_log).

        Returns:
            Result.ok(data=risk_dict) or Result.fail(...)
        """
        default = {
            "risk_level": "P3_噪音",
            "confidence": 0.0,
            "attack_type": "",
            "risk_desc": "常规日志记录，无异常特征",
            "suggestion": "",
            "match_rule_ids": [],
        }

        if not parsed_fields:
            return Result.ok(data=default)

        try:
            rules = JsonConfigLoader.load("risk_rules.json")
        except (FileNotFoundError, ValueError, Exception) as e:
            logger.warning(f"Could not load risk_rules.json: {e}")
            return Result.ok(data=default)

        best_match = None
        best_confidence = 0.0

        for rule in rules:
            condition = rule.get("condition", {})
            if self._evaluate_condition(condition, parsed_fields):
                confidence = rule.get("confidence", 0.5) * rule.get("weight", 1.0)
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = {
                        "risk_level": rule.get("risk_level", default["risk_level"]),
                        "confidence": confidence,
                        "attack_type": rule.get("attack_type", ""),
                        "risk_desc": rule.get("risk_desc", default["risk_desc"]),
                        "suggestion": rule.get("suggestion", ""),
                        "match_rule_ids": [rule.get("rule_id", "")],
                    }
                elif confidence == best_confidence and best_match:
                    if rule.get("rule_id"):
                        best_match["match_rule_ids"].append(rule.get("rule_id"))

        if best_match:
            best_match["confidence"] = round(best_match["confidence"], 4)
            return Result.ok(data=best_match)

        return Result.ok(data=default)

    @staticmethod
    def _evaluate_condition(condition: Dict[str, Any],
                            parsed_fields: Dict[str, Any]) -> bool:
        """
        Evaluate a single risk rule condition against parsed fields.

        Supported operators:
          - eq: field value equals the given value
          - contains_any: field text contains any of the keywords
          - startswith: field value starts with one of the given values
          - always_true: always matches
        """
        operator = condition.get("operator", "eq")
        field = condition.get("field", "")
        value = condition.get("value")
        keywords = condition.get("keywords")

        if operator == "always_true":
            return True

        field_value = parsed_fields.get(field)

        if field_value is None:
            if field == "time_range":
                return True
            return False

        if operator == "eq":
            return str(field_value).lower() == str(value).lower()

        if operator == "contains_any":
            if not keywords:
                return False
            return _contains_any(str(field_value), keywords)

        if operator == "startswith":
            if isinstance(value, list):
                return any(str(field_value).startswith(v) for v in value)
            return str(field_value).startswith(str(value))

        logger.debug(f"Unknown condition operator: {operator}")
        return False

    # ------------------------------------------------------------------
    # batch_parse
    # ------------------------------------------------------------------

    def batch_parse(self, logs: List[str], do_assess: bool = False) -> Dict[str, Any]:
        """
        Parse a batch of log lines.

        Args:
            logs: List of raw log line strings.
            do_assess: If True, run risk assessment on each parsed result.

        Returns:
            dict with keys:
              total: total number of logs processed
              success_count: number of successfully parsed logs
              fail_count: number of logs that could not be parsed
              items: list of parsed result dicts
              risk_summary: aggregated risk summary (when do_assess=True)
        """
        total = len(logs)
        items: List[Dict[str, Any]] = []
        success_count = 0
        fail_count = 0
        risk_summary: Dict[str, Any] = {
            "total_assessed": 0,
            "high_risk_count": 0,
            "medium_risk_count": 0,
            "low_risk_count": 0,
            "noise_count": 0,
        }

        for log_line in logs:
            if not log_line or not log_line.strip():
                fail_count += 1
                items.append({
                    "raw_log": log_line,
                    "device_type": "unknown",
                    "error": "Empty log line",
                })
                continue

            parse_result = self.parse_log(log_line)
            parsed = parse_result.get("data", {})
            item: Dict[str, Any] = {
                "raw_log": parsed.get("raw_log", log_line),
                "device_type": parsed.get("device_type", "unknown"),
                "timestamp": parsed.get("timestamp"),
                "src_ip": parsed.get("src_ip"),
                "dst_ip": parsed.get("dst_ip"),
                "user": parsed.get("user"),
                "status": parsed.get("status"),
                "command": parsed.get("command"),
                "extra_info": parsed.get("extra_info", {}),
            }

            if parsed.get("device_type") != "unknown" or any(
                v for v in [parsed.get("timestamp"), parsed.get("src_ip"),
                            parsed.get("user"), parsed.get("status")]
            ):
                success_count += 1
            else:
                fail_count += 1
                item["error"] = "Could not identify or parse log type"

            if do_assess:
                risk_result = self.assess_risk(parsed)
                risk = risk_result.get("data", {})
                item["risk_assessment"] = risk
                risk_summary["total_assessed"] += 1
                rl = risk.get("risk_level", "P3_噪音")
                if rl.startswith("P0"):
                    risk_summary["high_risk_count"] += 1
                elif rl.startswith("P1"):
                    risk_summary["medium_risk_count"] += 1
                elif rl.startswith("P2"):
                    risk_summary["low_risk_count"] += 1
                else:
                    risk_summary["noise_count"] += 1

            items.append(item)

        return {
            "total": total,
            "success_count": success_count,
            "fail_count": fail_count,
            "items": items,
            "risk_summary": risk_summary if do_assess else {},
        }

    # ------------------------------------------------------------------
    # explain_field
    # ------------------------------------------------------------------

    def explain_field(self, field_name: str,
                      device_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Return an explanation of a log field.

        Args:
            field_name: Name of the field to explain.
            device_type: Optional device type for context-specific explanation.

        Returns:
            dict with keys: field, explanation, device_type
        """
        base_explanations = {
            "timestamp": "时间戳记录了日志事件发生的具体时间，格式通常为 ISO 8601 或 Syslog 格式",
            "src_ip": "源IP地址表示发起连接或请求的客户端IP地址",
            "dst_ip": "目标IP地址表示接收连接或请求的服务端IP地址",
            "user": "用户名表示执行操作或发起登录请求的用户身份标识",
            "status": "状态表示操作的结果或当前会话的状态，如成功、失败、连接中",
            "command": "命令表示在会话中执行的具体指令或SQL查询语句",
            "device_type": "设备类型表示日志来源的设备或服务类型，如 ssh、web、firewall",
            "raw_log": "原始日志是未经处理的完整日志文本行",
            "extra_info": "附加信息包含与该日志相关的额外字段和上下文数据",
        }

        device_specific = {
            "ssh": {
                "status": "SSH登录状态: failed=密码验证失败, success=登录成功, session_opened=会话开启, session_closed=会话关闭, sudo=sudo命令执行",
                "user": "SSH登录尝试使用的用户名",
                "command": "通过sudo执行的命令内容",
                "src_ip": "发起SSH连接的客户端IP地址",
            },
            "web": {
                "status": "HTTP响应状态码，如200=成功, 404=未找到, 500=服务器错误",
                "command": "HTTP请求的URL路径",
                "user": "HTTP认证用户名(如存在)",
                "src_ip": "发起HTTP请求的客户端IP地址",
            },
            "waf": {
                "status": "WAF处理动作: blocked=已拦截, alert=告警, allowed=已放行",
                "src_ip": "被WAF检测的请求源IP地址",
                "extra_info": "包含攻击类型(attack_type)、规则ID(rule_id)、严重级别(severity)等WAF详细信息",
            },
            "firewall": {
                "status": "防火墙处理动作: dropped=丢弃, rejected=拒绝, accepted=接受, denied=拒绝",
                "src_ip": "防火墙规则匹配的数据包源IP(SRC)",
                "dst_ip": "防火墙规则匹配的数据包目标IP(DST)",
                "extra_info": "包含协议(PROTO)、源端口(SPT)、目标端口(DPT)、接口(IN/OUT)等防火墙详细信息",
            },
            "db": {
                "status": "数据库连接或操作状态: error=错误, connect=连接, disconnect=断开, query=查询",
                "user": "数据库登录用户名",
                "command": "执行的SQL查询或语句",
                "extra_info": "包含数据库类型(db_type)、数据库名(database_name)、错误码(error_code)等详细信息",
            },
        }

        explanation = base_explanations.get(
            field_name, f"'{field_name}' 是日志中的自定义字段"
        )

        if device_type and device_type in device_specific:
            if field_name in device_specific[device_type]:
                explanation = device_specific[device_type][field_name]

        return {
            "field": field_name,
            "explanation": explanation,
            "device_type": device_type or "any",
        }