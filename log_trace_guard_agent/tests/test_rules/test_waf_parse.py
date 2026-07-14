"""WAF 解析器单元测试"""

import pytest
from modules.log_parse.waf_parse import WAFParser


class TestWAFParser:
    def setup_method(self):
        self.parser = WAFParser()

    def test_waf_modsecurity_format(self):
        log = '[Wed Oct 11 14:32:23 2023] [error] [client 192.168.1.100] Attack detected from 192.168.1.100'
        assert self.parser.can_parse(log)
        result = self.parser.parse_fields(log)
        assert result["device_type"] == "waf"
        assert result["src_ip"] == "192.168.1.100"

    def test_waf_generic_format(self):
        log = '2023-10-11 14:32:23 [WAF] BLOCKED 192.168.1.100 GET /wp-admin SQL_INJECTION'
        assert self.parser.can_parse(log)
        result = self.parser.parse_fields(log)
        assert result["device_type"] == "waf"
        assert result["src_ip"] == "192.168.1.100"
        assert result["method"] == "GET"
        assert result["url"] == "/wp-admin"
        assert result["attack_type"] == "SQL注入"

    def test_waf_attack_classification(self):
        log = '2023-10-11 14:32:23 [WAF] BLOCKED 10.0.0.5 POST /login XSS'
        assert self.parser.can_parse(log)
        result = self.parser.parse_fields(log)
        assert result["attack_type"] == "XSS跨站脚本"

    def test_waf_malformed_input(self, sample_malformed_inputs):
        for log in sample_malformed_inputs:
            assert not self.parser.can_parse(log)

    def test_waf_empty_input(self):
        assert not self.parser.can_parse("")
