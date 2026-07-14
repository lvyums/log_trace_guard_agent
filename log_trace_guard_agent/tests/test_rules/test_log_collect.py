"""日志采集架构指导模块单元测试 — 覆盖 P0/P1/P2/P3 整改场景"""

import pytest
import time
from modules.log_collect.collect_strategy import (
    CollectStrategyFactory, BaseCollectStrategy,
    SyslogCollectStrategy, FileCollectStrategy, DBSyncCollectStrategy,
    GenericSyslogStrategy,
)
from modules.log_collect.device_match import DeviceMatcher, DeviceMatchResult
from modules.log_collect.fault_fix import FaultFixer, FaultDiagnosis
from modules.log_collect.service import LogCollectService
from app.exceptions import ParamInvalidException


# ── P0: 工厂解耦测试 ──

class TestCollectStrategyFactory:
    """P0: 工厂注册模式测试 — 禁止硬编码策略"""

    def setup_method(self):
        CollectStrategyFactory.clear()
        # 重新注册默认策略
        CollectStrategyFactory.register(SyslogCollectStrategy())
        CollectStrategyFactory.register(FileCollectStrategy())
        CollectStrategyFactory.register(DBSyncCollectStrategy())

    def test_factory_register_strategy(self):
        """P0: 工厂通过 register() 注册策略，非硬编码"""
        assert len(CollectStrategyFactory._strategies) == 3  # Syslog + File + DB

    def test_factory_get_plan_returns_valid(self):
        """P0: 工厂 get_plan 始终返回有效方案（兜底策略保证）"""
        plan = CollectStrategyFactory.get_plan("firewall", "paloalto", "small")
        assert plan is not None
        assert plan.protocol == "syslog"

    def test_factory_fallback_for_unknown_type(self):
        """P0: 未知设备类型返回兜底方案，不返回空"""
        plan = CollectStrategyFactory.get_plan("unknown_device_xyz", "", "small")
        assert plan is not None
        assert plan.device_type == "generic"

    def test_factory_get_supported_types(self):
        """P0: 获取所有支持的设备类型"""
        types = CollectStrategyFactory.get_supported_types()
        assert "firewall" in types
        assert "server" in types

    def test_syslog_strategy_match(self):
        strategy = SyslogCollectStrategy()
        assert strategy.match("firewall")
        assert strategy.match("waf")
        assert not strategy.match("server")

    def test_file_strategy_match(self):
        strategy = FileCollectStrategy()
        assert strategy.match("server")
        assert strategy.match("web")
        assert not strategy.match("firewall")

    def test_get_plan_server(self):
        plan = CollectStrategyFactory.get_plan("server", "linux", "small")
        assert plan is not None
        assert plan.protocol == "file"

    def test_get_plan_db(self):
        plan = CollectStrategyFactory.get_plan("db", "mysql", "small")
        assert plan is not None
        assert plan.protocol == "db_sync"

    def test_generic_syslog_fallback(self):
        """P0: GenericSyslogStrategy 兜底策略测试"""
        strategy = GenericSyslogStrategy()
        assert strategy.match("anything")  # 兜底策略永远匹配
        plan = strategy.generate_plan("custom_device", "small")
        assert plan.device_type == "generic"


# ── P0: 上下文隔离测试 ──

class TestContextManager:
    """P0: 上下文管理器 TTL 过期 + 请求隔离"""

    def test_context_create_with_ttl(self):
        from core.context_manager import ContextManager
        ctx = ContextManager.create("test", ttl_seconds=60)
        assert ctx.request_id.startswith("req_")
        assert not ctx.is_expired()

    def test_context_isolated_by_request_id(self):
        """P0: 不同请求的上下文互不干扰"""
        from core.context_manager import ContextManager
        import time
        ctx1 = ContextManager.create("input1")
        time.sleep(0.01)  # 确保时间戳不同
        ctx2 = ContextManager.create("input2")
        assert ctx1.request_id != ctx2.request_id

    def test_context_cleanup_expired(self):
        """P0: 过期上下文自动清理"""
        from core.context_manager import ContextManager
        ctx = ContextManager.create("test", ttl_seconds=0)
        import time
        time.sleep(0.01)
        assert ctx.is_expired()
        cleaned = ContextManager.cleanup_expired()
        assert cleaned >= 1


# ── P1: 外部配置测试 ──

class TestDeviceMatcher:
    """P1: 设备匹配器 — 外部配置驱动 + 置信度"""

    def test_match_by_model_paloalto(self):
        result = DeviceMatcher.match_by_model("PA-5260 paloalto")
        assert result is not None
        assert result.device_type == "firewall"
        assert result.vendor == "Palo Alto"
        assert result.match_confidence > 90

    def test_match_by_model_nginx(self):
        result = DeviceMatcher.match_by_model("nginx/1.18.0")
        assert result is not None
        assert result.device_type == "web"

    def test_match_by_model_unknown(self):
        result = DeviceMatcher.match_by_model("Unknown Device XYZ")
        assert result is None

    def test_match_by_log_sample_ssh(self):
        log = "sshd[1234]: Accepted password for root from 192.168.1.1 port 22"
        result = DeviceMatcher.match_by_log_sample(log)
        assert result is not None
        assert result.device_type == "server"
        assert result.match_confidence > 0

    def test_match_by_log_sample_web(self):
        log = '192.168.1.1 - - [10/Oct/2023:13:55:36 +0000] "GET /index.html HTTP/1.1" 200'
        result = DeviceMatcher.match_by_log_sample(log)
        assert result is not None
        assert result.device_type == "web"

    def test_get_recommendation_returns_confidence(self):
        """P1: 推荐结果包含置信度"""
        rec = DeviceMatcher.get_recommendation("firewall", "paloalto", "small")
        assert "match_confidence" in rec
        assert rec["match_confidence"] > 0


# ── P1+P2: 故障诊断测试 ──

class TestFaultFixer:
    """P1+P2: 故障诊断 — 外部知识库 + 多维度匹配"""

    def test_diagnose_log_lost(self):
        diagnosis = FaultFixer.diagnose("日志丢失严重，采集到的数量只有一半")
        assert diagnosis is not None
        assert diagnosis.fault_type == "日志丢失"
        assert diagnosis.match_score > 0

    def test_diagnose_with_protocol_hint(self):
        """P2: 多维度诊断 — 传输协议辅助匹配"""
        diagnosis = FaultFixer.diagnose("日志丢失", protocol="syslog")
        assert diagnosis is not None
        assert "日志丢失" in diagnosis.fault_type

    def test_diagnose_format_error(self):
        diagnosis = FaultFixer.diagnose("日志格式错乱，无法解析")
        assert diagnosis is not None
        assert diagnosis.fault_type == "格式错乱"

    def test_diagnose_unknown(self):
        diagnosis = FaultFixer.diagnose("完全不相关的描述xyz123")
        assert diagnosis is None

    def test_get_all_faults(self):
        faults = FaultFixer.get_all_faults()
        assert len(faults) > 0
        assert all("fault_type" in f for f in faults)

    def test_get_fault_detail(self):
        detail = FaultFixer.get_fault_detail("日志丢失")
        assert detail is not None
        assert len(detail.possible_causes) > 0

    def test_diagnose_with_error_log(self):
        """P2: 多维度诊断 — 原始报错日志辅助匹配"""
        diagnosis = FaultFixer.diagnose(
            "采集异常",
            error_log="syslog: connection timed out, 丢包严重"
        )
        assert diagnosis is not None


# ── P2: 参数校验测试 ──

class TestServiceValidation:
    """P2: 全链路参数校验"""

    @pytest.mark.asyncio
    async def test_match_device_empty_type(self):
        """P2: 空设备类型抛出 ParamInvalidException"""
        with pytest.raises(ParamInvalidException):
            await LogCollectService.match_device(device_type="")

    @pytest.mark.asyncio
    async def test_match_device_invalid_scale(self):
        """P2: 无效规模参数抛出异常"""
        with pytest.raises(ParamInvalidException):
            await LogCollectService.match_device(device_type="firewall", scale="invalid")

    @pytest.mark.asyncio
    async def test_diagnose_empty_symptom(self):
        """P2: 空症状描述抛出异常"""
        with pytest.raises(ParamInvalidException):
            await LogCollectService.diagnose_fault(symptom="")

    @pytest.mark.asyncio
    async def test_batch_empty_devices(self):
        """P2: 空设备列表抛出异常"""
        with pytest.raises(ParamInvalidException):
            await LogCollectService.batch_generate_plans(devices=[])

    @pytest.mark.asyncio
    async def test_batch_too_many_devices(self):
        """P2: 超过50台设备抛出异常"""
        devices = [{"device_type": "firewall"} for _ in range(51)]
        with pytest.raises(ParamInvalidException):
            await LogCollectService.batch_generate_plans(devices=devices)


# ── P3: 批量接口测试 ──

class TestBatchPlan:
    """P3: 批量采集方案生成"""

    @pytest.mark.asyncio
    async def test_batch_generate_success(self):
        devices = [
            {"device_type": "firewall", "device_model": "paloalto"},
            {"device_type": "server", "device_model": "linux"},
            {"device_type": "db", "device_model": "mysql"},
        ]
        result = await LogCollectService.batch_generate_plans(devices=devices)
        assert result["code"] == 0
        assert result["data"]["total"] == 3
        assert result["data"]["success_count"] == 3

    @pytest.mark.asyncio
    async def test_batch_protocol_summary(self):
        """P3: 批量结果包含协议分布汇总"""
        devices = [
            {"device_type": "firewall"},
            {"device_type": "firewall"},
            {"device_type": "server"},
        ]
        result = await LogCollectService.batch_generate_plans(devices=devices)
        summary = result["data"]["protocol_summary"]
        assert "syslog" in summary
        assert summary["syslog"] == 2
