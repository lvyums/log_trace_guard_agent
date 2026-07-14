"""防火墙解析器单元测试"""

import pytest
from modules.log_parse.firewall_parse import FirewallParser


class TestFirewallParser:
    def setup_method(self):
        self.parser = FirewallParser()

    def test_iptables_ufw_block(self):
        log = 'Oct 11 14:32:23 server kernel: [UFW BLOCK] IN=eth0 OUT= SRC=192.168.1.100 DST=10.0.0.1 PROTO=TCP SPT=54321 DPT=22'
        assert self.parser.can_parse(log)
        result = self.parser.parse_fields(log)
        assert result["device_type"] == "firewall"
        assert result["src_ip"] == "192.168.1.100"
        assert result["dst_ip"] == "10.0.0.1"
        assert result["protocol"] == "TCP"
        assert result["src_port"] == "54321"
        assert result["dst_port"] == "22"
        assert result["status"] == "blocked"

    def test_pf_block(self):
        log = 'Oct 11 14:32:23 fw01 pf: block in on em0 from 192.168.1.100 to 10.0.0.1 proto tcp port 22'
        assert self.parser.can_parse(log)
        result = self.parser.parse_fields(log)
        assert result["device_type"] == "firewall"
        assert result["src_ip"] == "192.168.1.100"
        assert result["dst_ip"] == "10.0.0.1"
        assert result["protocol"] == "tcp"
        assert result["status"] == "blocked"

    def test_commercial_firewall(self):
        log = 'Oct 11 14:32:23 firewall01 DENY TCP 192.168.1.100:54321 -> 10.0.0.1:22'
        assert self.parser.can_parse(log)
        result = self.parser.parse_fields(log)
        assert result["device_type"] == "firewall"
        assert result["src_ip"] == "192.168.1.100"
        assert result["dst_ip"] == "10.0.0.1"
        assert result["protocol"] == "TCP"
        assert result["status"] == "blocked"

    def test_firewall_malformed_input(self, sample_malformed_inputs):
        for log in sample_malformed_inputs:
            assert not self.parser.can_parse(log)

    def test_firewall_empty_input(self):
        assert not self.parser.can_parse("")
