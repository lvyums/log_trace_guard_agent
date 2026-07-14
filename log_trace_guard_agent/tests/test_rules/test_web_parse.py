"""Web 解析器单元测试"""

import pytest
from modules.log_parse.web_parse import WebParser


class TestWebParser:
    def setup_method(self):
        self.parser = WebParser()

    def test_web_combined_format(self, sample_web_logs):
        log = sample_web_logs[0]
        assert self.parser.can_parse(log)
        result = self.parser.parse_fields(log)
        assert result["device_type"] == "web"
        assert result["src_ip"] == "192.168.1.1"
        assert result["method"] == "GET"
        assert result["url"] == "/index.html"
        assert result["status"] == "200"
        assert result["user_agent"] == "Mozilla/5.0"

    def test_web_common_format(self, sample_web_logs):
        log = sample_web_logs[2]
        assert self.parser.can_parse(log)
        result = self.parser.parse_fields(log)
        assert result["src_ip"] == "192.168.1.100"
        assert result["method"] == "GET"
        assert result["url"] == "/admin"
        assert result["status"] == "403"

    def test_web_attack_pattern(self, sample_web_logs):
        log = sample_web_logs[1]
        result = self.parser.parse_fields(log)
        assert result["method"] == "POST"
        assert "wp-admin" in result["url"]

    def test_web_malformed_input(self, sample_malformed_inputs):
        for log in sample_malformed_inputs:
            assert not self.parser.can_parse(log)

    def test_web_empty_input(self):
        assert not self.parser.can_parse("")