"""日志采集架构指导模块单元测试"""

import pytest
from modules.log_collect.collect_strategy import CollectStrategyFactory, SyslogCollectStrategy, FileCollectStrategy
from modules.log_collect.device_match import DeviceMatcher
from modules.log_collect.fault_fix import FaultFixer


class TestCollectStrategy:
    def setup_method(self):
        self.factory = CollectStrategyFactory()

    def test_syslog_strategy_match(self):
        strategy = SyslogCollectStrategy()
        assert strategy.match("firewall")
        assert strategy.match("waf")
        assert strategy.match("ids")
        assert not strategy.match("server")

    def test_file_strategy_match(self):
        strategy = FileCollectStrategy()
        assert strategy.match("server")
        assert strategy.match("web")
        assert strategy.match("nginx")
        assert not strategy.match("firewall")

    def test_get_plan_firewall(self):
        plan = CollectStrategyFactory.get_plan("firewall", "paloalto", "small")
        assert plan is not None
        assert plan.protocol == "syslog"
        assert len(plan.steps) > 0

    def test_get_plan_server(self):
        plan = CollectStrategyFactory.get_plan("server", "linux", "small")
        assert plan is not None
        assert plan.protocol == "file"

    def test_get_plan_unknown(self):
        plan = CollectStrategyFactory.get_plan("unknown_device")
        assert plan is None

    def test_get_supported_types(self):
        types = CollectStrategyFactory.get_supported_types()
        assert "firewall" in types
        assert "server" in types
        assert "db" in types


class TestDeviceMatcher:
    def test_match_by_model_paloalto(self):
        info = DeviceMatcher.match_by_model("PA-5260 paloalto")
        assert info is not None
        assert info.device_type == "firewall"
        assert info.vendor == "Palo Alto"

    def test_match_by_model_nginx(self):
        info = DeviceMatcher.match_by_model("nginx/1.18.0")
        assert info is not None
        assert info.device_type == "web"
        assert info.vendor == "Nginx"

    def test_match_by_model_unknown(self):
        info = DeviceMatcher.match_by_model("Unknown Device XYZ")
        assert info is None

    def test_match_by_log_sample_ssh(self):
        log = "sshd[1234]: Accepted password for root from 192.168.1.1 port 22"
        info = DeviceMatcher.match_by_log_sample(log)
        assert info is not None
        assert info.device_type == "server"

    def test_match_by_log_sample_web(self):
        log = '192.168.1.1 - - [10/Oct/2023:13:55:36 +0000] "GET /index.html HTTP/1.1" 200'
        info = DeviceMatcher.match_by_log_sample(log)
        assert info is not None
        assert info.device_type == "web"


class TestFaultFixer:
    def test_diagnose_log_lost(self):
        diagnosis = FaultFixer.diagnose("日志丢失严重，采集到的数量只有实际的一半")
        assert diagnosis is not None
        assert diagnosis.fault_type == "日志丢失"
        assert len(diagnosis.fix_steps) > 0

    def test_diagnose_format_error(self):
        diagnosis = FaultFixer.diagnose("日志格式错乱，无法解析")
        assert diagnosis is not None
        assert diagnosis.fault_type == "格式错乱"

    def test_diagnose_unknown(self):
        diagnosis = FaultFixer.diagnose("完全不相关的描述")
        assert diagnosis is None

    def test_get_all_faults(self):
        faults = FaultFixer.get_all_faults()
        assert len(faults) > 0
        assert all("fault_type" in f for f in faults)

    def test_get_fault_detail(self):
        detail = FaultFixer.get_fault_detail("日志丢失")
        assert detail is not None
        assert len(detail.possible_causes) > 0
        assert len(detail.fix_steps) > 0
