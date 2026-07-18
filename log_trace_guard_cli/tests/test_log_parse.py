"""Tests for modules/log_parse.py — parsers, factory, and service."""
import json
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from log_guard.modules.log_parse import (
    SSHParser,
    WebParser,
    WAFParser,
    FirewallParser,
    DBParser,
    LogParserFactory,
    LogParseService,
    LogParseResult,
    get_default_factory,
)


# =========================================================================
# SSH Parser Tests
# =========================================================================

class TestSSHParser(unittest.TestCase):
    def setUp(self):
        self.parser = SSHParser()

    def test_can_parse_sshd(self):
        self.assertTrue(self.parser.can_parse("sshd[1234]: Failed password for root"))

    def test_can_parse_sudo(self):
        self.assertTrue(self.parser.can_parse("sudo: pam_unix(sudo:session): session opened"))

    def test_can_parse_accepted(self):
        self.assertTrue(self.parser.can_parse("sshd[1234]: Accepted publickey for admin"))

    def test_cannot_parse_web(self):
        self.assertFalse(self.parser.can_parse('GET /index.html HTTP/1.1" 200'))

    def test_parse_failed_password(self):
        result = self.parser.parse('sshd[1234]: Failed password for root from 192.168.1.100 port 22 ssh2')
        self.assertIsNotNone(result)
        self.assertEqual(result.device_type, "ssh")
        self.assertEqual(result.src_ip, "192.168.1.100")
        self.assertEqual(result.user, "root")
        self.assertEqual(result.status, "failed")

    def test_parse_accepted_password(self):
        result = self.parser.parse('sshd[1234]: Accepted password for admin from 10.0.0.1 port 22 ssh2')
        self.assertIsNotNone(result)
        self.assertEqual(result.src_ip, "10.0.0.1")
        self.assertEqual(result.user, "admin")
        self.assertEqual(result.status, "success")

    def test_parse_session_opened(self):
        result = self.parser.parse('sshd[1234]: pam_unix(sshd:session): session opened for user dev')
        self.assertIsNotNone(result)
        self.assertEqual(result.status, "session_opened")

    def test_parse_sudo(self):
        result = self.parser.parse('sudo: pam_unix(sudo:session): session opened for user root')
        self.assertIsNotNone(result)
        self.assertEqual(result.status, "session_opened")

    def test_parse_extracts_port(self):
        result = self.parser.parse('sshd[1234]: Failed password for root from 192.168.1.100 port 2222 ssh2')
        self.assertIsNotNone(result)
        self.assertEqual(result.extra_info.get("port"), "2222")

    def test_parse_empty_line(self):
        result = self.parser.parse("")
        self.assertIsNone(result)

    def test_parse_invalid(self):
        result = self.parser.parse("random text without ssh keywords")
        self.assertIsNone(result)

    def test_to_dict(self):
        result = LogParseResult(
            timestamp="2024-01-01T10:00:00",
            src_ip="1.2.3.4",
            user="admin",
            device_type="ssh",
            raw_log="test log",
        )
        d = result.to_dict()
        self.assertIn("timestamp", d)
        self.assertIn("src_ip", d)
        self.assertIn("user", d)
        self.assertIn("device_type", d)
        self.assertIn("raw_log", d)
        self.assertNotIn("dst_ip", d)  # None values excluded
        self.assertNotIn("status", d)

    def test_to_dict_all(self):
        result = LogParseResult(src_ip="1.2.3.4")
        d = result.to_dict_all()
        self.assertIn("src_ip", d)
        self.assertIn("dst_ip", d)  # None included


# =========================================================================
# Web Parser Tests
# =========================================================================

class TestWebParser(unittest.TestCase):
    def setUp(self):
        self.parser = WebParser()

    def test_can_parse_get(self):
        self.assertTrue(self.parser.can_parse('192.168.1.1 - - [10/Jan/2024:12:00:00 +0000] "GET /index.html HTTP/1.1" 200 1234'))

    def test_can_parse_post(self):
        self.assertTrue(self.parser.can_parse('"POST /login HTTP/1.1"'))

    def test_cannot_parse_ssh(self):
        self.assertFalse(self.parser.can_parse("sshd: Failed password"))

    def test_parse_get_request(self):
        line = '192.168.1.1 - admin [10/Jan/2024:12:00:00 +0000] "GET /index.html HTTP/1.1" 200 1234'
        result = self.parser.parse(line)
        self.assertIsNotNone(result)
        self.assertEqual(result.device_type, "web")
        self.assertEqual(result.src_ip, "192.168.1.1")
        self.assertEqual(result.status, "200")
        self.assertEqual(result.user, "admin")
        self.assertEqual(result.extra_info.get("http_method"), "GET")
        self.assertEqual(result.extra_info.get("response_size"), "1234")

    def test_parse_extracts_url(self):
        line = '1.2.3.4 - - [10/Jan/2024:12:00:00] "POST /api/login HTTP/1.1" 401 500'
        result = self.parser.parse(line)
        self.assertIsNotNone(result)
        self.assertEqual(result.extra_info.get("url"), "/api/login")

    def test_parse_user_agent(self):
        line = '1.2.3.4 - - [10/Jan/2024:12:00:00] "GET / HTTP/1.1" 200 1234 "Mozilla/5.0"'
        result = self.parser.parse(line)
        self.assertIsNotNone(result)
        self.assertIn("Mozilla", result.extra_info.get("user_agent", ""))


# =========================================================================
# WAF Parser Tests
# =========================================================================

class TestWAFParser(unittest.TestCase):
    def setUp(self):
        self.parser = WAFParser()

    def test_can_parse_waf(self):
        self.assertTrue(self.parser.can_parse("WAF: blocked SQL injection attempt"))

    def test_can_parse_modsecurity(self):
        self.assertTrue(self.parser.can_parse("ModSecurity: Alert from 1.2.3.4"))

    def test_cannot_parse_normal(self):
        self.assertFalse(self.parser.can_parse("normal syslog message"))

    def test_parse_blocked(self):
        result = self.parser.parse("WAF: blocked SQL injection from 10.0.0.5")
        self.assertIsNotNone(result)
        self.assertEqual(result.status, "blocked")
        self.assertEqual(result.device_type, "waf")
        self.assertEqual(result.extra_info.get("attack_type"), "SQL Injection")

    def test_parse_alert(self):
        result = self.parser.parse("ModSecurity: Alert from 192.168.1.1 rule=1234")
        self.assertIsNotNone(result)
        self.assertEqual(result.status, "alert")
        self.assertEqual(result.extra_info.get("rule_id"), "1234")

    def test_parse_xss(self):
        result = self.parser.parse("WAF: XSS detected from 1.2.3.4 severity=high")
        self.assertIsNotNone(result)
        self.assertEqual(result.extra_info.get("attack_type"), "XSS")
        self.assertEqual(result.extra_info.get("severity"), "high")

    def test_parse_path_traversal(self):
        result = self.parser.parse("WAF: blocked path traversal ../etc/passwd from 1.2.3.4")
        self.assertIsNotNone(result)
        self.assertEqual(result.extra_info.get("attack_type"), "Path Traversal")


# =========================================================================
# Firewall Parser Tests
# =========================================================================

class TestFirewallParser(unittest.TestCase):
    def setUp(self):
        self.parser = FirewallParser()

    def test_can_parse_iptables(self):
        self.assertTrue(self.parser.can_parse("IN=eth0 OUT= SRC=1.2.3.4 DST=5.6.7.8"))

    def test_can_parse_drop(self):
        self.assertTrue(self.parser.can_parse("DROP IN=eth0 SRC=1.2.3.4"))

    def test_cannot_parse_ssh(self):
        self.assertFalse(self.parser.can_parse("sshd: Failed password"))

    def test_parse_drop(self):
        line = "Jan 15 10:30:00 server kernel: DROP IN=eth0 OUT= SRC=10.0.0.1 DST=10.0.0.2 PROTO=TCP SPT=12345 DPT=80 LEN=40"
        result = self.parser.parse(line)
        self.assertIsNotNone(result)
        self.assertEqual(result.status, "dropped")
        self.assertEqual(result.src_ip, "10.0.0.1")
        self.assertEqual(result.dst_ip, "10.0.0.2")
        self.assertEqual(result.extra_info.get("protocol"), "TCP")
        self.assertEqual(result.extra_info.get("src_port"), "12345")
        self.assertEqual(result.extra_info.get("dst_port"), "80")
        self.assertEqual(result.extra_info.get("packet_length"), "40")

    def test_parse_accept(self):
        result = self.parser.parse("ACCEPT IN=eth0 SRC=10.0.0.1 DST=10.0.0.2 PROTO=UDP SPT=53 DPT=12345")
        self.assertIsNotNone(result)
        self.assertEqual(result.status, "accepted")


# =========================================================================
# DB Parser Tests
# =========================================================================

class TestDBParser(unittest.TestCase):
    def setUp(self):
        self.parser = DBParser()

    def test_can_parse_mysql(self):
        self.assertTrue(self.parser.can_parse("mysql: connect from 1.2.3.4"))

    def test_can_parse_postgres(self):
        self.assertTrue(self.parser.can_parse("postgres: ERROR: syntax error"))

    def test_cannot_parse_ssh(self):
        self.assertFalse(self.parser.can_parse("sshd: Failed password"))

    def test_parse_query(self):
        result = self.parser.parse("mysql: 2024-01-01T10:00:00 user=app query=SELECT * FROM users")
        self.assertIsNotNone(result)
        self.assertEqual(result.status, "query")
        self.assertEqual(result.extra_info.get("db_type"), "MySQL")

    def test_parse_error(self):
        result = self.parser.parse("postgres: ERROR: syntax error at or near 'DROP'")
        self.assertIsNotNone(result)
        self.assertEqual(result.status, "error")
        self.assertEqual(result.extra_info.get("db_type"), "PostgreSQL")

    def test_parse_connect(self):
        result = self.parser.parse("mysql: 2024-01-01T10:00:00 connect from app@10.0.0.1")
        self.assertIsNotNone(result)
        self.assertEqual(result.status, "connect")


# =========================================================================
# LogParserFactory Tests
# =========================================================================

class TestLogParserFactory(unittest.TestCase):
    def setUp(self):
        self.factory = LogParserFactory()
        self.factory.register("ssh", SSHParser, "sshd", "secure")
        self.factory.register("web", WebParser, "http", "apache")

    def test_get_parser_ssh(self):
        parser = self.factory.get_parser("sshd: Failed password for root")
        self.assertIsNotNone(parser)
        self.assertIsInstance(parser, SSHParser)

    def test_get_parser_web(self):
        parser = self.factory.get_parser('GET /index.html HTTP/1.1" 200')
        self.assertIsNotNone(parser)
        self.assertIsInstance(parser, WebParser)

    def test_get_parser_unknown(self):
        parser = self.factory.get_parser("some completely unknown log format")
        self.assertIsNone(parser)

    def test_get_parser_by_type(self):
        parser = self.factory.get_parser_by_type("ssh")
        self.assertIsNotNone(parser)
        self.assertIsInstance(parser, SSHParser)

    def test_get_parser_by_alias(self):
        parser = self.factory.get_parser_by_type("sshd")
        self.assertIsNotNone(parser)
        self.assertIsInstance(parser, SSHParser)

    def test_get_parser_by_type_unknown(self):
        parser = self.factory.get_parser_by_type("nonexistent")
        self.assertIsNone(parser)

    def test_parse_method(self):
        result = self.factory.parse("sshd: Failed password for root from 10.0.0.1")
        self.assertIsNotNone(result)
        self.assertIsInstance(result, dict)
        self.assertEqual(result["device_type"], "ssh")

    def test_parse_method_unknown(self):
        result = self.factory.parse("garbage text")
        self.assertIsNone(result)

    def test_parser_caching(self):
        a = self.factory.get_parser("sshd: test")
        b = self.factory.get_parser("sshd: test2")
        self.assertIs(a, b)  # Same cached instance

    def test_registered_types(self):
        types = self.factory.registered_types
        self.assertIn("ssh", types)
        self.assertIn("web", types)

    def test_registered_aliases(self):
        aliases = self.factory.registered_aliases
        self.assertEqual(aliases.get("ssh"), "ssh")
        self.assertEqual(aliases.get("sshd"), "ssh")
        self.assertEqual(aliases.get("http"), "web")


# =========================================================================
# LogParseService Tests
# =========================================================================

class TestLogParseService(unittest.TestCase):
    def setUp(self):
        self.service = LogParseService()

    def test_identify_log_type_ssh(self):
        result = self.service.identify_log_type("sshd: Failed password for root from 10.0.0.1")
        self.assertIn(result["device_type"], ("ssh", "unknown"))
        self.assertGreaterEqual(result["confidence"], 0.0)

    def test_identify_log_type_empty(self):
        result = self.service.identify_log_type("")
        self.assertEqual(result["device_type"], "unknown")
        self.assertEqual(result["confidence"], 0.0)

    def test_identify_log_type_whitespace(self):
        result = self.service.identify_log_type("   ")
        self.assertEqual(result["device_type"], "unknown")

    def test_parse_log_ssh(self):
        result = self.service.parse_log("sshd: Failed password for root from 10.0.0.1 port 22")
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get("src_ip"), "10.0.0.1")
        self.assertEqual(result.get("user"), "root")
        self.assertEqual(result.get("status"), "failed")
        self.assertIn("raw_log", result)

    def test_parse_log_empty(self):
        result = self.service.parse_log("")
        self.assertIsInstance(result, dict)
        self.assertEqual(result["device_type"], "unknown")

    def test_parse_log_web(self):
        line = '1.2.3.4 - - [10/Jan/2024:12:00:00 +0000] "GET /index.html HTTP/1.1" 200 1234'
        result = self.service.parse_log(line)
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get("src_ip"), "1.2.3.4")
        self.assertEqual(result.get("status"), "200")

    def test_parse_log_unknown(self):
        result = self.service.parse_log("some completely random log line")
        self.assertIsInstance(result, dict)
        self.assertEqual(result["device_type"], "unknown")

    def test_assess_risk_empty(self):
        result = self.service.assess_risk({})
        self.assertIn("risk_level", result)
        self.assertIn("confidence", result)

    def test_assess_risk_ssh_failed(self):
        parsed = {
            "device_type": "ssh",
            "status": "failed",
            "src_ip": "10.0.0.1",
            "user": "root",
        }
        result = self.service.assess_risk(parsed)
        self.assertIn("risk_level", result)
        self.assertIn("match_rule_ids", result)

    def test_batch_parse_empty(self):
        result = self.service.batch_parse([])
        self.assertEqual(result["total"], 0)
        self.assertEqual(result["success_count"], 0)

    def test_batch_parse_normal(self):
        logs = [
            "sshd: Failed password for root from 10.0.0.1",
            "sshd: Accepted password for admin from 10.0.0.2",
            "garbage line",
        ]
        result = self.service.batch_parse(logs)
        self.assertEqual(result["total"], 3)
        self.assertGreaterEqual(result["success_count"], 2)

    def test_batch_parse_with_risk(self):
        logs = [
            "sshd: Failed password for root from 10.0.0.1",
            "sshd: Accepted password for admin from 10.0.0.2",
        ]
        result = self.service.batch_parse(logs, do_assess=True)
        self.assertEqual(result["total"], 2)
        self.assertIn("risk_summary", result)
        self.assertGreaterEqual(result["risk_summary"]["total_assessed"], 0)


    def test_explain_field_known(self):
        result = self.service.explain_field("src_ip")
        self.assertEqual(result["field"], "src_ip")
        self.assertIn("explanation", result)

    def test_explain_field_unknown(self):
        result = self.service.explain_field("custom_field_x")
        self.assertEqual(result["field"], "custom_field_x")
        self.assertIn("explanation", result)

    def test_explain_field_device_specific(self):
        result = self.service.explain_field("status", device_type="ssh")
        self.assertIn("SSH", result["explanation"])

    def test_explain_field_device_specific_waf(self):
        result = self.service.explain_field("status", device_type="waf")
        self.assertIn("WAF", result["explanation"])

    def test_parse_log_preserves_raw(self):
        raw = "sshd: test message"
        result = self.service.parse_log(raw)
        self.assertEqual(result["raw_log"], raw)


class TestDefaultFactory(unittest.TestCase):
    def test_get_default_factory(self):
        factory = get_default_factory()
        self.assertIsNotNone(factory)
        # Should have all default parsers
        types = factory.registered_types
        self.assertIn("ssh", types)
        self.assertIn("web", types)
        self.assertIn("waf", types)
        self.assertIn("firewall", types)
        self.assertIn("db", types)

    def test_default_factory_singleton(self):
        a = get_default_factory()
        b = get_default_factory()
        self.assertIs(a, b)


if __name__ == "__main__":
    unittest.main()