"""攻击链 → 实训场景 (/to-scenario) 链路自动化测试

覆盖五层：
1. TemporalAnalyzer._fallback_scenario — LLM 失败时的降级方案（纯函数）
2. TemporalAnalyzer.generate_training — LLM 场景生成（成功 / markdown 包裹 / LLM 失败降级）
3. TaskEngine.inject_scenario — 动态场景注入后 dispatch / get_scenario / get_standard_answer 可访问
4. LogCorrelateService.to_training_scenario — 动态模式（chain_data）/ 传统模式（无 chain_data）/ 异常降级
5. API 集成 — POST /api/v1/log-correlate/to-scenario
"""

import json

import pytest
from httpx import AsyncClient, ASGITransport

from core.ai_base.llm_factory import LLMFactory
from modules.log_correlate.service import LogCorrelateService
from modules.log_correlate.temporal import TemporalAnalyzer
from modules.training.task_engine import TaskEngine
from app.main import app


# ── 测试数据 ──

SSH_LOG_LINES = [
    "Mar 15 10:30:25 server sshd[1234]: Accepted password for root from 192.168.1.1 port 22",
    "Mar 15 10:31:00 server sshd[1235]: Failed password for admin from 10.0.0.5 port 22",
    "Mar 15 10:32:00 server sshd[1236]: Failed password for admin from 10.0.0.5 port 22",
]

CHAIN_DATA = {
    "chain_name": "ssh_brute_force",
    "description": "SSH 暴力破解攻击链",
    "risk_level": "P1_高危",
    "indicators": ["192.168.1.1", "10.0.0.5"],
    "matched_keywords": ["Failed password", "Accepted password"],
    "temporal": {
        "timeline": [
            {"timestamp": "10:31:00", "stage": "爆破", "keyword": "Failed password", "src_ip": "10.0.0.5"},
            {"timestamp": "10:32:00", "stage": "爆破", "keyword": "Failed password", "src_ip": "10.0.0.5"},
        ],
        "stages_observed": ["爆破"],
    },
    "suggestion": "封禁 10.0.0.5 并排查 root 账户",
}

VALID_TRAINING_JSON = {
    "scenario": {
        "name": "SSH 暴力破解实战溯源",
        "description": "基于真实 SSH 爆破日志的实战训练",
        "category": "实战",
        "difficulty": "中级",
        "objectives": ["识别攻击类型", "提取关键证据"],
    },
    "tasks": [
        {"task_id": "T01", "order": 1, "title": "攻击类型识别", "description": "判断攻击类型",
         "input_type": "log_lines", "submit_type": "conclusion", "hint": "关注认证失败"},
        {"task_id": "T02", "order": 2, "title": "关键证据提取", "description": "提取攻击源 IP",
         "input_type": "text", "submit_type": "conclusion", "hint": "关注 src_ip"},
    ],
    "standard_answers": {
        "T01": {"attack_type": "ssh_brute_force", "risk_level": "P1_高危", "key_indicators": ["192.168.1.1"]},
        "T02": {"src_ip": "192.168.1.1", "evidence_count": 3},
    },
}


# ── Mock LLM ──

class MockLLMClient:
    """模拟 LLM 客户端 — chat 返回预置响应"""

    def __init__(self, response: dict):
        self._response = response

    async def chat(self, messages, temperature=None, timeout=None, max_tokens=None):
        return self._response


async def _mock_llm(monkeypatch, response: dict):
    """替换 LLMFactory.get_light_llm 返回固定响应的假客户端"""

    async def fake_get_light_llm():
        return MockLLMClient(response)

    monkeypatch.setattr(LLMFactory, "get_light_llm", fake_get_light_llm)


@pytest.fixture(autouse=True)
def _clean_dynamic_scenarios():
    """每个测试前后清理 TaskEngine 动态场景，避免类级状态污染"""
    TaskEngine._dynamic_scenarios.clear()
    TaskEngine._dynamic_answers.clear()
    yield
    TaskEngine._dynamic_scenarios.clear()
    TaskEngine._dynamic_answers.clear()


# ── 1. _fallback_scenario 降级方案 ──

class TestFallbackScenario:
    def test_fallback_structure(self):
        result = TemporalAnalyzer._fallback_scenario(CHAIN_DATA, SSH_LOG_LINES)
        assert "scenario" in result
        assert "tasks" in result
        assert "standard_answers" in result
        assert len(result["tasks"]) == 4
        assert result["scenario"]["category"] == "实战"
        assert result["scenario"]["difficulty"] == "中级"
        assert "实战溯源" in result["scenario"]["name"]
        assert len(result["scenario"]["objectives"]) >= 3

    def test_fallback_tasks_fields(self):
        result = TemporalAnalyzer._fallback_scenario(CHAIN_DATA, SSH_LOG_LINES)
        task_ids = [t["task_id"] for t in result["tasks"]]
        assert task_ids == ["T01", "T02", "T03", "T04"]
        for t in result["tasks"]:
            assert t["title"]
            assert t["description"]
            assert t["input_type"] in ("log_lines", "text")
            assert t["submit_type"] in ("conclusion", "plan")
            assert "hint" in t

    def test_fallback_answers_use_chain_data(self):
        result = TemporalAnalyzer._fallback_scenario(CHAIN_DATA, SSH_LOG_LINES)
        answers = result["standard_answers"]
        # fallback 标准答案从真实日志/攻击链数据提取（中文可评分，非占位符）
        assert "暴力破解" in answers["T01"]["attack_type"]
        assert "高危" in answers["T01"]["risk_level"]
        assert "192.168.1.1" in answers["T01"]["key_indicators"]
        assert answers["T03"]["evidence_count"] == len(SSH_LOG_LINES)

    def test_fallback_empty_input(self):
        result = TemporalAnalyzer._fallback_scenario({}, [])
        assert result["scenario"]["name"] == "实战溯源：unknown"
        assert result["standard_answers"]["T03"]["evidence_count"] == 0


# ── 2. generate_training LLM 场景生成 ──

class TestGenerateTraining:
    @pytest.mark.asyncio
    async def test_success(self, monkeypatch):
        await _mock_llm(monkeypatch, {"success": True, "content": json.dumps(VALID_TRAINING_JSON, ensure_ascii=False)})
        result = await TemporalAnalyzer.generate_training(CHAIN_DATA, SSH_LOG_LINES)
        assert result["scenario"]["name"] == "SSH 暴力破解实战溯源"
        assert len(result["tasks"]) == 2
        assert result["standard_answers"]["T01"]["attack_type"] == "ssh_brute_force"

    @pytest.mark.asyncio
    async def test_markdown_wrapped(self, monkeypatch):
        content = "```json\n" + json.dumps(VALID_TRAINING_JSON, ensure_ascii=False) + "\n```"
        await _mock_llm(monkeypatch, {"success": True, "content": content})
        result = await TemporalAnalyzer.generate_training(CHAIN_DATA, SSH_LOG_LINES)
        assert result["scenario"]["name"] == "SSH 暴力破解实战溯源"
        assert len(result["tasks"]) == 2

    @pytest.mark.asyncio
    async def test_llm_failure_falls_back(self, monkeypatch):
        await _mock_llm(monkeypatch, {"success": False, "error": "API 402 欠费"})
        result = await TemporalAnalyzer.generate_training(CHAIN_DATA, SSH_LOG_LINES)
        assert result["scenario"]["category"] == "实战"
        assert len(result["tasks"]) == 4  # fallback 固定 4 任务

    @pytest.mark.asyncio
    async def test_empty_chain_data(self):
        result = await TemporalAnalyzer.generate_training(None, SSH_LOG_LINES)
        assert result["scenario"] is None
        assert result["tasks"] == []
        assert result["standard_answers"] == {}


# ── 3. TaskEngine 动态场景注入 ──

class TestTaskEngineInjection:
    def test_inject_and_query(self):
        scenario_id = TaskEngine.inject_scenario(
            scenario={
                "name": "实战溯源：SSH 爆破",
                "description": "基于真实攻击链的实战训练",
                "category": "实战",
                "difficulty": "中级",
                "objectives": ["识别攻击类型"],
                "tasks": [
                    {"task_id": "T01", "order": 1, "title": "攻击类型识别", "description": "d",
                     "input_type": "log_lines", "submit_type": "conclusion", "hint": "h"},
                ],
            },
            standard_answers={"T01": {"attack_type": "ssh_brute_force"}},
        )
        assert scenario_id.startswith("DYN_")

        # dispatch 能查到注入的场景
        dispatched = TaskEngine.dispatch(scenario_id=scenario_id)
        assert len(dispatched) == 1
        assert dispatched[0]["scenario"]["scenario_id"] == scenario_id
        assert dispatched[0]["total_tasks"] == 1
        assert dispatched[0]["tasks"][0]["task_id"] == "T01"

        # get_scenario / get_standard_answer 能查到
        sc = TaskEngine.get_scenario(scenario_id)
        assert sc["name"] == "实战溯源：SSH 爆破"
        ans = TaskEngine.get_standard_answer(scenario_id, "T01")
        assert ans["attack_type"] == "ssh_brute_force"

    def test_dispatch_unknown_scenario_empty(self):
        assert TaskEngine.dispatch(scenario_id="DYN_999999_999") == []


# ── 4. LogCorrelateService.to_training_scenario ──

class TestToTrainingScenario:
    @pytest.mark.asyncio
    async def test_dynamic_mode_success(self, monkeypatch):
        await _mock_llm(monkeypatch, {"success": True, "content": json.dumps(VALID_TRAINING_JSON, ensure_ascii=False)})
        result = await LogCorrelateService.to_training_scenario(
            log_lines=SSH_LOG_LINES,
            chain_name="ssh_brute_force",
            chain_description="SSH 暴力破解",
            chain_data=CHAIN_DATA,
        )
        assert result["code"] == 0
        scenarios = result["data"]["scenarios"]
        assert len(scenarios) == 1
        assert scenarios[0]["_dynamic"] is True
        assert scenarios[0]["scenario"]["name"] == "SSH 暴力破解实战溯源"
        assert scenarios[0]["total_tasks"] == 2
        assert scenarios[0]["tasks"][0]["input_data"] == SSH_LOG_LINES[:50]

    @pytest.mark.asyncio
    async def test_dynamic_mode_llm_failure_uses_fallback(self, monkeypatch):
        await _mock_llm(monkeypatch, {"success": False, "error": "API 402 欠费"})
        result = await LogCorrelateService.to_training_scenario(
            log_lines=SSH_LOG_LINES,
            chain_name="ssh_brute_force",
            chain_description="SSH 暴力破解",
            chain_data=CHAIN_DATA,
        )
        assert result["code"] == 0
        scenarios = result["data"]["scenarios"]
        assert len(scenarios) == 1
        assert scenarios[0]["_dynamic"] is True
        assert "实战溯源" in scenarios[0]["scenario"]["name"]
        assert scenarios[0]["total_tasks"] == 4

    @pytest.mark.asyncio
    async def test_traditional_mode(self):
        # 不传 chain_data → 按攻击链名称推断分类下发预置场景（ssh_brute_force → basic）
        result = await LogCorrelateService.to_training_scenario(
            log_lines=SSH_LOG_LINES,
            chain_name="ssh_brute_force",
            chain_description="SSH 暴力破解",
            chain_data=None,
        )
        assert result["code"] == 0
        assert result["data"]["total"] >= 1
        # 传统模式无 _dynamic 标记
        assert all("_dynamic" not in s for s in result["data"]["scenarios"])

    @pytest.mark.asyncio
    async def test_dynamic_exception_falls_back_to_traditional(self, monkeypatch):
        async def boom(*args, **kwargs):
            raise RuntimeError("LLM 不可用")

        monkeypatch.setattr(TemporalAnalyzer, "generate_training", boom)
        result = await LogCorrelateService.to_training_scenario(
            log_lines=SSH_LOG_LINES,
            chain_name="ssh_brute_force",
            chain_description="SSH 暴力破解",
            chain_data=CHAIN_DATA,
        )
        assert result["code"] == 0
        scenarios = result["data"]["scenarios"]
        assert scenarios  # 降级到传统模式仍有预置场景
        assert all("_dynamic" not in s for s in scenarios)


# ── 5. API 集成 ──

class TestToScenarioAPI:
    @pytest.mark.asyncio
    async def test_api_dynamic_mode(self, monkeypatch):
        await _mock_llm(monkeypatch, {"success": True, "content": json.dumps(VALID_TRAINING_JSON, ensure_ascii=False)})
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post("/api/v1/log-correlate/to-scenario", json={
                "log_lines": SSH_LOG_LINES,
                "chain_name": "ssh_brute_force",
                "chain_description": "SSH 暴力破解",
                "chain_data": CHAIN_DATA,
            })
            assert r.status_code == 200
            data = r.json()
            assert data["code"] == 0
            assert data["data"]["scenarios"][0]["_dynamic"] is True
            assert data["data"]["scenarios"][0]["total_tasks"] == 2

    @pytest.mark.asyncio
    async def test_api_traditional_mode(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post("/api/v1/log-correlate/to-scenario", json={
                "log_lines": SSH_LOG_LINES,
                "chain_name": "sql_injection",
                "chain_description": "SQL 注入攻击",
            })
            assert r.status_code == 200
            data = r.json()
            assert data["code"] == 0
            assert data["data"]["total"] >= 1
