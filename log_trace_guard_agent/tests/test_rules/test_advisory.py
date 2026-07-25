"""模块六：规划咨询 — 单元测试"""

import pytest
import json
import os
import sys

# 确保项目根目录在 sys.path 中
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from modules.advisory.arch_strategy import ArchitectureRecommendStrategy, arch_recommend_strategy
from modules.advisory.platform_strategy import PlatformChooseStrategy, platform_choose_strategy
from modules.advisory.service import AdvisoryService
from app.exceptions import ParamInvalidException


# ══════════════════════════════════════════════════════════════
# ArchitectureRecommendStrategy 测试
# ══════════════════════════════════════════════════════════════

class TestArchitectureRecommendStrategy:
    """架构推荐策略测试"""

    def setup_method(self):
        self.strategy = ArchitectureRecommendStrategy()

    def test_recommend_small_enterprise(self):
        """正常场景：小微企业推荐"""
        result = self.strategy.recommend(device_count=10, daily_log_volume="small")
        assert "arch_name" in result
        assert result["arch_name"] != ""

    def test_recommend_medium_enterprise(self):
        """正常场景：中型企业推荐"""
        result = self.strategy.recommend(device_count=100, daily_log_volume="medium")
        assert "arch_name" in result

    def test_recommend_large_enterprise(self):
        """正常场景：大型企业推荐"""
        result = self.strategy.recommend(device_count=1000, daily_log_volume="large")
        assert "arch_name" in result

    def test_recommend_returns_valid_structure(self):
        """验证返回结构包含必要字段"""
        result = self.strategy.recommend(device_count=50, daily_log_volume="small")
        assert isinstance(result, dict)
        # 至少应包含 arch_name 或 architecture_desc
        assert "arch_name" in result or "architecture_desc" in result


# ══════════════════════════════════════════════════════════════
# PlatformChooseStrategy 测试
# ══════════════════════════════════════════════════════════════

class TestPlatformChooseStrategy:
    """平台选型推荐策略测试"""

    def setup_method(self):
        self.strategy = PlatformChooseStrategy()

    def test_recommend_small_enterprise(self):
        """正常场景：小微企业推荐"""
        result = self.strategy.recommend(
            device_count=10,
            daily_log_volume="small",
            budget="low",
            team_skill="basic",
        )
        assert "recommendation" in result
        assert result["recommendation"]["name"]
        assert "summary" in result

    def test_recommend_large_enterprise(self):
        """正常场景：大型企业推荐"""
        result = self.strategy.recommend(
            device_count=5000,
            daily_log_volume="large",
            budget="high",
            team_skill="advanced",
            requirements=["安全分析", "合规报告"],
        )
        assert "recommendation" in result
        assert "alternatives" in result
        assert len(result["alternatives"]) >= 0

    def test_recommend_with_requirements(self):
        """正常场景：带附加需求"""
        result = self.strategy.recommend(
            device_count=100,
            daily_log_volume="medium",
            budget="medium",
            team_skill="intermediate",
            requirements=["全文检索", "可视化"],
        )
        assert result["recommendation"]["name"]

    def test_fallback_empty_platforms(self):
        """边界场景：无匹配平台时使用兜底"""
        # 使用极端参数确保无匹配
        result = self.strategy.recommend(
            device_count=999999,
            daily_log_volume="unknown",
            budget="unknown",
            team_skill="unknown",
        )
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

    def test_recommend_returns_valid_structure(self):
        """验证返回结构包含必要字段"""
        result = self.strategy.recommend(device_count=50)
        assert "recommendation" in result
        assert "alternatives" in result
        assert "summary" in result


# ══════════════════════════════════════════════════════════════
# AdvisoryService 测试
# ══════════════════════════════════════════════════════════════

class TestAdvisoryService:
    """业务编排层测试"""

    @pytest.mark.asyncio
    async def test_recommend_architecture_success(self):
        """正常场景：架构推荐成功"""
        result = await AdvisoryService.recommend_architecture(
            device_count=50,
            daily_log_volume="medium",
        )
        assert result["code"] == 0
        assert "arch_name" in result["data"]

    @pytest.mark.asyncio
    async def test_recommend_architecture_invalid_device_count(self):
        """边界场景：无效设备数量"""
        with pytest.raises(ParamInvalidException):
            await AdvisoryService.recommend_architecture(device_count=0)

    @pytest.mark.asyncio
    async def test_recommend_architecture_invalid_volume(self):
        """边界场景：无效日志量级"""
        with pytest.raises(ParamInvalidException):
            await AdvisoryService.recommend_architecture(
                device_count=10,
                daily_log_volume="invalid",
            )

    @pytest.mark.asyncio
    async def test_recommend_platform_success(self):
        """正常场景：平台选型成功"""
        result = await AdvisoryService.recommend_platform(
            device_count=100,
            daily_log_volume="medium",
            budget="medium",
        )
        assert result["code"] == 0
        assert "recommendation" in result["data"]

    @pytest.mark.asyncio
    async def test_recommend_platform_invalid_device_count(self):
        """边界场景：无效设备数量"""
        with pytest.raises(ParamInvalidException):
            await AdvisoryService.recommend_platform(device_count=0)

    @pytest.mark.asyncio
    async def test_recommend_platform_with_requirements(self):
        """正常场景：带附加需求"""
        result = await AdvisoryService.recommend_platform(
            device_count=200,
            requirements=["全文检索", "安全分析"],
        )
        assert result["code"] == 0
        assert result["data"]["recommendation"]["name"]


# ══════════════════════════════════════════════════════════════
# 配置加载验证
# ══════════════════════════════════════════════════════════════

class TestConfigLoading:
    """外部配置加载验证"""

    def test_arch_templates_config_exists(self):
        """验证架构模板配置文件存在"""
        path = os.path.join(project_root, "data/rule_data/arch_templates.json")
        assert os.path.exists(path), f"配置文件不存在: {path}"
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_platform_fallback_config_exists(self):
        """验证平台兜底配置文件存在"""
        path = os.path.join(project_root, "data/rule_data/script_gen_platform_fallback.json")
        assert os.path.exists(path), f"配置文件不存在: {path}"
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        assert "name" in data

    def test_platforms_config_exists(self):
        """验证平台配置文件存在"""
        path = os.path.join(project_root, "data/rule_data/script_gen_platforms.json")
        assert os.path.exists(path), f"配置文件不存在: {path}"
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, list)
        assert len(data) > 0
