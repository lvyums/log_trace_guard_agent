"""模块四：技术赋能脚本生成 — 单元测试"""

import pytest
import json
import os
import sys

# 确保项目根目录在 sys.path 中
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from modules.script_gen.regex_gen import RegexGenStrategy
from modules.script_gen.es_sql_gen import ESQueryGenStrategy
from modules.script_gen.platform_choose import PlatformChooseStrategy
from modules.script_gen.trace_link import TraceLinkStrategy
from modules.script_gen.service import ScriptGenService


# ══════════════════════════════════════════════════════════════
# RegexGenStrategy 测试
# ══════════════════════════════════════════════════════════════

class TestRegexGenStrategy:
    """正则规则生成策略测试"""

    def setup_method(self):
        self.strategy = RegexGenStrategy()

    def test_can_handle_valid_scenario(self):
        """正常场景：有 scenario 参数时 can_handle 返回 True"""
        assert self.strategy.can_handle({"scenario": "SSH爆破攻击"}) is True

    def test_can_handle_empty_scenario(self):
        """边界场景：空 scenario 时返回 False"""
        assert self.strategy.can_handle({"scenario": ""}) is False
        assert self.strategy.can_handle({}) is False

    def test_can_handle_whitespace_scenario(self):
        """边界场景：纯空格 scenario 时返回 False"""
        assert self.strategy.can_handle({"scenario": "   "}) is False

    def test_generate_ssh_scenario(self):
        """正常场景：SSH爆破场景生成正则规则"""
        result = self.strategy.generate({"scenario": "SSH爆破攻击"})
        assert "regexes" in result
        assert len(result["regexes"]) > 0
        assert result["scenario"] == "SSH爆破攻击"
        # 验证返回的规则包含必要字段
        for rule in result["regexes"]:
            assert "name" in rule
            assert "pattern" in rule
            assert "description" in rule
            assert "priority" in rule

    def test_generate_with_log_sample(self):
        """正常场景：带日志样例生成正则"""
        log_sample = "sshd[1234]: Failed password for root from 192.168.1.1 port 22"
        result = self.strategy.generate({
            "scenario": "SSH爆破",
            "log_sample": log_sample,
        })
        assert len(result["regexes"]) > 0

    def test_generate_unknown_scenario(self):
        """边界场景：未知场景生成通用规则"""
        result = self.strategy.generate({"scenario": "一个非常特殊的攻击场景描述"})
        assert len(result["regexes"]) > 0  # 有兜底
        # 兜底规则应有通用名称
        assert result["note"] is not None

    def test_generate_web_scenario(self):
        """正常场景：Web攻击场景"""
        result = self.strategy.generate({"scenario": "SQL注入攻击", "device_type": "web"})
        assert len(result["regexes"]) > 0
        assert any("sql" in r["name"].lower() or "注入" in r["name"] for r in result["regexes"])

    def test_identify_scene_ssh(self):
        """场景识别：SSH关键词识别"""
        scene = self.strategy._identify_scene("SSH爆破登录失败")
        assert scene == "ssh"

    def test_identify_scene_unknown(self):
        """场景识别：无匹配关键词时返回 unknown"""
        scene = self.strategy._identify_scene("完全无关的随机文本")
        assert scene == "unknown"


# ══════════════════════════════════════════════════════════════
# ESQueryGenStrategy 测试
# ══════════════════════════════════════════════════════════════

class TestESQueryGenStrategy:
    """ES 检索语句生成策略测试"""

    def setup_method(self):
        self.strategy = ESQueryGenStrategy()

    def test_can_handle_valid(self):
        """正常场景：有 search_scenario 时返回 True"""
        assert self.strategy.can_handle({"search_scenario": "SSH爆破"}) is True

    def test_can_handle_empty(self):
        """边界场景：空参数时返回 False"""
        assert self.strategy.can_handle({}) is False
        assert self.strategy.can_handle({"search_scenario": ""}) is False

    def test_generate_ssh_brute(self):
        """正常场景：SSH爆破场景生成 ES 查询"""
        result = self.strategy.generate({"search_scenario": "SSH爆破攻击"})
        assert "query" in result
        assert "explanation" in result
        # 验证 query 是合法 JSON
        query = json.loads(result["query"])
        assert "query" in query or "bool" in query

    def test_generate_unknown_scenario(self):
        """边界场景：未知场景生成通用查询"""
        result = self.strategy.generate({"search_scenario": "一个非常特殊的查询场景"})
        assert "query" in result
        # 说明应该包含通用检索
        assert "通用" in result["explanation"] or "全文检索" in result["explanation"]

    def test_generate_with_time_range(self):
        """正常场景：带时间范围参数"""
        result = self.strategy.generate({
            "search_scenario": "SSH爆破",
            "time_range": "last_7d",
        })
        query = json.loads(result["query"])
        # 验证有时间过滤 — query 结构可能是 {query: {bool: ...}} 或 {bool: ...}
        bool_part = query.get("query", {}).get("bool") or query.get("bool", {})
        filters = bool_part.get("filter", [])
        has_time_filter = any(
            "range" in f and "@timestamp" in f["range"]
            for f in filters
        )
        assert has_time_filter

    def test_build_time_filter(self):
        """时间过滤器构建"""
        time_filter = self.strategy._build_time_filter("last_24h")
        assert time_filter["range"]["@timestamp"]["gte"] == "now-24h"
        assert time_filter["range"]["@timestamp"]["lte"] == "now"

    def test_build_time_filter_default(self):
        """边界场景：未知时间范围使用默认值"""
        time_filter = self.strategy._build_time_filter("unknown_range")
        assert time_filter["range"]["@timestamp"]["gte"] is not None

    def test_identify_scene_sql(self):
        """场景识别：SQL注入场景"""
        scene = self.strategy._identify_scene("检测SQL注入攻击")
        assert scene == "sql_injection"

    def test_identify_scene_unknown(self):
        """场景识别：无匹配时返回 unknown"""
        scene = self.strategy._identify_scene("随机文本")
        assert scene == "unknown"


# ══════════════════════════════════════════════════════════════
# PlatformChooseStrategy 测试
# ══════════════════════════════════════════════════════════════

class TestPlatformChooseStrategy:
    """平台选型推荐策略测试"""

    def setup_method(self):
        self.strategy = PlatformChooseStrategy()

    def test_can_handle_valid(self):
        """正常场景：有 device_count 时返回 True"""
        assert self.strategy.can_handle({"device_count": 100}) is True

    def test_can_handle_empty(self):
        """边界场景：无参数时返回 False"""
        assert self.strategy.can_handle({}) is False

    def test_generate_small_enterprise(self):
        """正常场景：小微企业推荐"""
        result = self.strategy.generate({
            "device_count": 10,
            "daily_log_volume": "small",
            "budget": "low",
            "team_skill": "basic",
        })
        assert "recommendation" in result
        assert result["recommendation"]["name"]
        assert "summary" in result

    def test_generate_large_enterprise(self):
        """正常场景：大型企业推荐"""
        result = self.strategy.generate({
            "device_count": 5000,
            "daily_log_volume": "large",
            "budget": "high",
            "team_skill": "advanced",
            "requirements": ["安全分析", "合规报告"],
        })
        assert "recommendation" in result
        assert "alternatives" in result
        assert len(result["alternatives"]) >= 0

    def test_generate_with_requirements(self):
        """正常场景：带附加需求"""
        result = self.strategy.generate({
            "device_count": 100,
            "daily_log_volume": "medium",
            "budget": "medium",
            "team_skill": "intermediate",
            "requirements": ["全文检索", "可视化"],
        })
        assert result["recommendation"]["name"]

    def test_fallback_empty_platforms(self):
        """边界场景：无匹配平台时使用兜底"""
        # 使用极端参数确保无匹配
        result = self.strategy.generate({
            "device_count": 999999,
            "daily_log_volume": "unknown",
            "budget": "unknown",
            "team_skill": "unknown",
        })
        assert result["recommendation"]["name"]  # 应有兜底推荐

    def test_score_platform(self):
        """评分计算验证"""
        platform = {
            "device_range": {"min": 10, "max": 5000},
            "supported_volumes": ["medium", "large"],
            "budget_level": ["medium", "high"],
            "required_skill": ["intermediate", "advanced"],
            "features": ["全文检索", "可视化", "水平扩展"],
        }
        score = self.strategy._score_platform(platform, 100, "medium", "medium", "intermediate", ["全文检索"])
        assert score > 0


# ══════════════════════════════════════════════════════════════
# TraceLinkStrategy 测试
# ══════════════════════════════════════════════════════════════

class TestTraceLinkStrategy:
    """攻击链路溯源策略测试"""

    def setup_method(self):
        self.strategy = TraceLinkStrategy()

    def test_can_handle_valid(self):
        """正常场景：有 logs 时返回 True"""
        assert self.strategy.can_handle({"logs": ["test log"]}) is True

    def test_can_handle_empty(self):
        """边界场景：无参数时返回 False"""
        assert self.strategy.can_handle({}) is False
        assert self.strategy.can_handle({"logs": []}) is False

    def test_generate_brute_force(self):
        """正常场景：SSH爆破攻击溯源"""
        logs = [
            "sshd[1234]: Failed password for root from 192.168.1.1 port 22",
            "sshd[1235]: Failed password for admin from 192.168.1.1 port 22",
            "sshd[1236]: Accepted password for root from 192.168.1.1 port 22",
        ]
        result = self.strategy.generate({"logs": logs})
        assert "attack_chain" in result
        assert len(result["attack_chain"]) > 0
        assert "summary" in result
        # 验证事件包含必要字段
        for event in result["attack_chain"]:
            assert "event_type" in event
            assert "action" in event
            assert "risk_level" in event

    def test_generate_sql_injection(self):
        """正常场景：SQL注入攻击溯源"""
        logs = [
            "GET /user?id=1 UNION SELECT * FROM users HTTP/1.1 from 10.0.0.5",
            "10.0.0.5 - - [01/Jan/2026:10:00:00] \"GET /admin HTTP/1.1\" 403",
        ]
        result = self.strategy.generate({"logs": logs})
        assert len(result["attack_chain"]) > 0
        # SQL注入应为高危
        sql_events = [e for e in result["attack_chain"] if "sql" in e["event_type"]]
        if sql_events:
            assert sql_events[0]["risk_level"] == "high"

    def test_generate_port_scan(self):
        """正常场景：端口扫描溯源"""
        logs = [
            "SRC=192.168.1.100 DST=10.0.0.1 PROTO=TCP SPT=54321 DPT=22 SYN scan",
            "SRC=192.168.1.100 DST=10.0.0.1 PROTO=TCP SPT=54322 DPT=80 SYN scan",
        ]
        result = self.strategy.generate({"logs": logs, "attack_type": "端口扫描"})
        assert len(result["attack_chain"]) > 0

    def test_generate_empty_logs(self):
        """边界场景：空日志列表"""
        result = self.strategy.generate({"logs": []})
        assert len(result["attack_chain"]) == 0
        assert "未检测到攻击行为" in result["summary"]

    def test_generate_normal_logs(self):
        """边界场景：正常日志（无攻击特征）"""
        result = self.strategy.generate({"logs": ["正常操作日志，用户登录成功"]})
        # 即使没有攻击特征，也应有兜底输出
        assert "attack_chain" in result
        assert "summary" in result

    def test_identify_attack_stage_progression(self):
        """攻击阶段判定验证"""
        # 高危事件 → 权限提升/入侵
        events = [{"risk_level": "high", "event_type": "sql_injection"}]
        assert self.strategy._identify_attack_stage(events) == "权限提升/入侵"

        # 中危事件 → 初始入侵
        events = [{"risk_level": "medium", "event_type": "brute_force"}]
        assert self.strategy._identify_attack_stage(events) == "初始入侵"

        # 低危事件 → 侦查探测
        events = [{"risk_level": "low", "event_type": "port_scan"}]
        assert self.strategy._identify_attack_stage(events) == "侦查探测"

        # 数据泄露 → 最高优先级
        events = [{"risk_level": "high", "event_type": "data_exfil"}]
        assert self.strategy._identify_attack_stage(events) == "数据窃取/破坏"

        # 横向移动
        events = [{"risk_level": "high", "event_type": "lateral_move"}]
        assert self.strategy._identify_attack_stage(events) == "横向移动"

    def test_identify_attack_stage_empty(self):
        """边界场景：空事件列表"""
        assert self.strategy._identify_attack_stage([]) == "未检测到攻击行为"

    def test_extract_timestamp_iso(self):
        """时间戳提取：ISO格式"""
        ts = self.strategy._extract_timestamp("2026-01-15T10:30:00 test log")
        assert ts == "2026-01-15T10:30:00"

    def test_extract_timestamp_syslog(self):
        """时间戳提取：Syslog格式"""
        ts = self.strategy._extract_timestamp("Jan 15 10:30:00 host sshd[1234]: test")
        assert ts is not None

    def test_extract_timestamp_http(self):
        """时间戳提取：HTTP格式"""
        ts = self.strategy._extract_timestamp('[15/Jan/2026:10:30:00 +0800] "GET / HTTP/1.1"')
        assert ts == "15/Jan/2026:10:30:00"

    def test_extract_timestamp_none(self):
        """边界场景：无时间戳"""
        ts = self.strategy._extract_timestamp("random text without timestamp")
        assert ts is None


# ══════════════════════════════════════════════════════════════
# ScriptGenService 测试
# ══════════════════════════════════════════════════════════════

class TestScriptGenService:
    """业务编排层测试"""

    @pytest.mark.asyncio
    async def test_generate_regex_empty_scenario(self):
        """边界场景：空场景生成"""
        # 空场景应该在 can_handle 阶段处理，但验证 service 不崩溃
        result = await ScriptGenService.generate_regex(scenario="")
        # 可能 fail 或返回兜底，但不应该抛异常
        assert result is not None

    @pytest.mark.asyncio
    async def test_optimize_script_empty(self):
        """边界场景：空脚本优化"""
        result = await ScriptGenService.optimize_script(script="")
        assert result["code"] != 0  # 应该返回失败
        assert "msg" in result

    @pytest.mark.asyncio
    async def test_optimize_script_valid_regex(self):
        """正常场景：有效正则优化"""
        result = await ScriptGenService.optimize_script(
            script=r"(\d{1,3}\.){3}\d{1,3}",
            script_type="regex",
        )
        assert result["code"] == 0
        data = result["data"]
        assert "score" in data
        assert data["score"] > 0

    @pytest.mark.asyncio
    async def test_optimize_script_invalid_regex(self):
        """边界场景：无效正则语法"""
        result = await ScriptGenService.optimize_script(
            script=r"[invalid regex(",
            script_type="regex",
        )
        assert result["code"] == 0
        data = result["data"]
        assert len(data["issues"]) > 0

    @pytest.mark.asyncio
    async def test_optimize_script_valid_es_query(self):
        """正常场景：有效 ES 查询优化"""
        result = await ScriptGenService.optimize_script(
            script=json.dumps({"query": {"match": {"message": "test"}}}),
            script_type="es_query",
        )
        assert result["code"] == 0
        data = result["data"]
        assert "score" in data

    @pytest.mark.asyncio
    async def test_optimize_script_invalid_json(self):
        """边界场景：无效 JSON"""
        result = await ScriptGenService.optimize_script(
            script="not json at all",
            script_type="es_query",
        )
        assert result["code"] == 0
        data = result["data"]
        assert len(data["issues"]) > 0

    @pytest.mark.asyncio
    async def test_trace_attack_empty_logs(self):
        """边界场景：空日志列表"""
        result = await ScriptGenService.trace_attack(logs=[])
        assert result["code"] != 0  # 应该返回失败

    @pytest.mark.asyncio
    async def test_trace_attack_too_many_logs(self):
        """边界场景：超过100条日志限制"""
        logs = [f"log {i}" for i in range(101)]
        result = await ScriptGenService.trace_attack(logs=logs)
        assert result["code"] != 0  # 应该返回失败

    @pytest.mark.asyncio
    async def test_generate_regex_batch(self):
        """正常场景：批量生成正则"""
        scenarios = [
            {"scenario": "SSH爆破"},
            {"scenario": "SQL注入"},
        ]
        result = await ScriptGenService.generate_regex_batch(scenarios)
        assert result["code"] == 0
        data = result["data"]
        assert data["total"] == 2
        assert data["success_count"] == 2

    def test_analyze_regex_empty(self):
        """正则分析：空字符串"""
        result = ScriptGenService._analyze_regex("")
        assert result["score"] == 0
        assert "为空" in result["issues"][0]

    def test_analyze_regex_valid(self):
        """正则分析：有效正则"""
        result = ScriptGenService._analyze_regex(r"\d+")
        assert result["score"] > 0

    def test_analyze_regex_invalid(self):
        """正则分析：语法错误"""
        result = ScriptGenService._analyze_regex(r"[invalid")
        assert result["score"] == 10
        assert "语法错误" in result["issues"][0]

    def test_analyze_es_query_valid(self):
        """ES查询分析：有效"""
        result = ScriptGenService._analyze_es_query(
            json.dumps({"query": {"match": {"field": "value"}}, "size": 100})
        )
        assert result["score"] > 50

    def test_analyze_es_query_invalid(self):
        """ES查询分析：无效JSON"""
        result = ScriptGenService._analyze_es_query("not json")
        assert result["score"] == 10
        assert "JSON 格式错误" in result["issues"][0]

    def test_analyze_es_query_large_size(self):
        """ES查询分析：size过大"""
        result = ScriptGenService._analyze_es_query(
            json.dumps({"query": {"match": {"field": "value"}}, "size": 99999})
        )
        assert "滚动查询" in result["issues"][0]


# ══════════════════════════════════════════════════════════════
# 配置加载验证
# ══════════════════════════════════════════════════════════════

class TestConfigLoading:
    """外部配置加载验证"""

    def test_scene_keywords_config_exists(self):
        """验证场景关键词配置文件存在"""
        path = os.path.join(project_root, "data/rule_data/script_gen_scene_keywords.json")
        assert os.path.exists(path), f"配置文件不存在: {path}"
        with open(path) as f:
            data = json.load(f)
        assert "regex" in data
        assert "es_query" in data
        assert len(data["regex"]) > 0

    def test_fallback_rules_config_exists(self):
        """验证兜底规则配置文件存在"""
        path = os.path.join(project_root, "data/rule_data/script_gen_fallback_rules.json")
        assert os.path.exists(path)
        with open(path) as f:
            data = json.load(f)
        assert "ssh" in data or "default" in data

    def test_time_map_config_exists(self):
        """验证时间映射配置文件存在"""
        path = os.path.join(project_root, "data/rule_data/script_gen_time_map.json")
        assert os.path.exists(path)
        with open(path) as f:
            data = json.load(f)
        assert "last_24h" in data
        assert "default" in data

    def test_trace_patterns_config_exists(self):
        """验证溯源模式配置文件存在"""
        path = os.path.join(project_root, "data/rule_data/script_gen_trace_patterns.json")
        assert os.path.exists(path)
        with open(path) as f:
            data = json.load(f)
        assert "attack_patterns" in data
        assert "risk_levels" in data
        assert "event_descriptions" in data

    def test_platform_fallback_config_exists(self):
        """验证平台兜底配置文件存在"""
        path = os.path.join(project_root, "data/rule_data/script_gen_platform_fallback.json")
        assert os.path.exists(path)
        with open(path) as f:
            data = json.load(f)
        assert "name" in data

    def test_scoring_config_exists(self):
        """验证评分阈值配置文件存在"""
        path = os.path.join(project_root, "data/rule_data/script_gen_scoring.json")
        assert os.path.exists(path)
        with open(path) as f:
            data = json.load(f)
        assert "regex" in data
        assert "es_query" in data