"""模块四：平台选型推荐策略 — 根据企业规模、预算、技能推荐日志分析平台"""

from modules.script_gen.script_strategy import BaseScriptStrategy
from common.json_util import JsonConfigLoader
from app.settings import settings


class PlatformChooseStrategy(BaseScriptStrategy):
    """平台选型推荐策略 — 配置化匹配矩阵"""

    strategy_type = "platform"
    strategy_name = "平台选型推荐"

    def can_handle(self, params: dict) -> bool:
        return bool(params.get("device_count"))

    def generate(self, params: dict) -> dict:
        device_count = params.get("device_count", 10)
        daily_log_volume = params.get("daily_log_volume", "medium")
        budget = params.get("budget", "medium")
        team_skill = params.get("team_skill", "basic")
        requirements = params.get("requirements", [])

        # 从外部配置加载平台数据
        config_path = f"{settings.rule_data_dir}/script_gen_platforms.json"
        platforms = JsonConfigLoader.load(config_path) or []

        # 评分 & 匹配
        scored = []
        for platform in platforms:
            score = self._score_platform(platform, device_count, daily_log_volume, budget, team_skill, requirements)
            if score > 0:
                scored.append((score, platform))

        scored.sort(key=lambda x: -x[0])

        # 推荐方案 + 备选
        recommendation = None
        alternatives = []
        for score, platform in scored:
            item = {
                "name": platform.get("name", ""),
                "type": platform.get("type", ""),
                "pros": platform.get("pros", []),
                "cons": platform.get("cons", []),
                "estimated_cost": platform.get("estimated_cost", ""),
                "suitable_scenario": platform.get("suitable_scenario", ""),
            }
            if recommendation is None:
                recommendation = item
            else:
                alternatives.append(item)

        if recommendation is None:
            recommendation = self._get_fallback_recommendation()

        summary = self._generate_summary(recommendation, device_count, daily_log_volume, budget)

        return {
            "recommendation": recommendation,
            "alternatives": alternatives,
            "summary": summary,
        }

    def _score_platform(self, platform: dict, device_count: int, volume: str, budget: str, skill: str, requirements: list) -> float:
        """计算平台匹配度分数"""
        score = 0.0

        # 设备数量匹配
        device_range = platform.get("device_range", {})
        min_devices = device_range.get("min", 0)
        max_devices = device_range.get("max", 999999)
        if min_devices <= device_count <= max_devices:
            score += 25

        # 日志量级匹配
        if volume in platform.get("supported_volumes", []):
            score += 20

        # 预算匹配
        budget_levels = platform.get("budget_level", [])
        if budget in budget_levels:
            score += 20

        # 技能匹配
        if skill in platform.get("required_skill", []):
            score += 15
        elif skill == "basic" and "intermediate" in platform.get("required_skill", []):
            score += 5  # 可接受的学习曲线

        # 需求匹配
        if requirements and platform.get("features"):
            feat_set = set(f.lower() for f in platform["features"])
            req_set = set(r.lower() for r in requirements)
            match_count = len(req_set & feat_set)
            if match_count > 0:
                score += min(match_count * 10, 20)

        return score

    def _get_fallback_recommendation(self) -> dict:
        """兜底推荐"""
        return {
            "name": "ELK Stack (Elasticsearch + Logstash + Kibana)",
            "type": "ELK集群",
            "pros": ["开源免费", "社区活跃", "生态丰富", "支持水平扩展"],
            "cons": ["运维复杂度较高", "资源消耗较大", "学习曲线陡峭"],
            "estimated_cost": "中（需3-5台服务器）",
            "suitable_scenario": "适合中型企业，有专职运维团队，日志量在TB级别",
        }

    def _generate_summary(self, recommendation: dict, device_count: int, volume: str, budget: str) -> str:
        """生成选型总结"""
        return (
            f"基于您的企业规模（{device_count}台设备，{volume}日志量级，{budget}预算），"
            f"推荐 **{recommendation.get('name', '')}**。"
            f"该方案{recommendation.get('suitable_scenario', '')}。"
        )