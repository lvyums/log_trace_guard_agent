"""SSH 解析器单元测试"""

import pytest
from modules.log_parse.ssh_parse import SSHParser


class TestSSHParser:
    def setup_method(self):
        self.parser = SSHParser()

    def test_ssh_success_login(self, sample_ssh_logs):
        log = sample_ssh_logs[0]
        assert self.parser.can_parse(log)
        result = self.parser.parse_fields(log)
        assert result.device_type == "ssh"
        assert result.src_ip == "192.168.1.1"
        assert result.user == "root"
        assert result.status == "success"

    def test_ssh_failed_login(self, sample_ssh_logs):
        log = sample_ssh_logs[1]
        assert self.parser.can_parse(log)
        result = self.parser.parse_fields(log)
        assert result.src_ip == "10.0.0.5"
        assert result.user == "admin"
        assert result.status == "failed"

    def test_ssh_sudo_command(self, sample_ssh_logs):
        log = sample_ssh_logs[2]
        assert self.parser.can_parse(log)
        result = self.parser.parse_fields(log)
        assert result.status == "command_executed"
        assert result.user == "root"
        assert "rm -rf" in result.command

    def test_ssh_malformed_input(self, sample_malformed_inputs):
        for log in sample_malformed_inputs:
            assert not self.parser.can_parse(log)

    def test_ssh_empty_input(self):
        assert not self.parser.can_parse("")
        result = self.parser.parse_fields("")
        assert result.device_type == "ssh"