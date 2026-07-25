"""架构推荐策略 — 根据设备数量和日志量级推荐架构方案"""

from common.json_util import JsonConfigLoader
from app.settings import settings


class ArchitectureRecommendStrategy:
    """架构推荐策略 — 配置化阈值匹配"""

    def __init__(self):
        self._config_cache = None

    def _load_config(self) -> dict:
        """加载架构模板配置"""
        if self._config_cache is None:
            config_path = f"{settings.rule_data_dir}/arch_templates.json"
            self._config_cache = JsonConfigLoader.load(config_path)
        return self._config_cache or {}

    def recommend(self, device_count: int, daily_log_volume: str) -> dict:
        """根据配置化阈值推荐架构"""
        templates = self._load_config()
        if not templates:
            return {"recommended_arch": "未知", "architecture_desc": "配置加载失败，请联系管理员"}

        if device_count <= settings.arch_small_device_count and daily_log_volume == settings.arch_small_log_volume:
            return templates.get("lightweight", {})
        elif device_count <= settings.arch_medium_device_count and daily_log_volume in ("small", "medium"):
            return templates.get("elk_cluster", {})
        else:
            return templates.get("enterprise_siem", {})


# 全局单例
arch_recommend_strategy = ArchitectureRecommendStrategy()
