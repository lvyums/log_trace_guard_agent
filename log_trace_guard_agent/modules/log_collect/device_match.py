"""设备类型匹配 — 外部配置驱动 + 置信度评估 + 日志特征识别（不依赖 log_parse 模块）"""

from dataclasses import dataclass
from typing import Optional

from common.logger import LogManager
from common.json_util import JsonConfigLoader

logger = LogManager.get_logger()


@dataclass
class DeviceMatchResult:
    """设备匹配结果 — 含置信度"""
    device_type: str
    device_model: str = ""
    vendor: str = ""
    log_format: str = ""
    recommended_protocol: str = ""
    match_confidence: float = 0.0   # 0~100 置信度
    match_source: str = ""          # "model" | "log_sample" | "type" | "fallback"


class DeviceMatcher:
    """设备类型匹配器 — 外部配置驱动，不依赖 log_parse 模块"""

    _config_cache: Optional[dict] = None

    @classmethod
    def _load_config(cls) -> dict:
        """加载设备型号映射配置"""
        if cls._config_cache is None:
            from app.settings import settings
            cls._config_cache = JsonConfigLoader.load(settings.device_protocol_data_path)
        return cls._config_cache or {}

    @classmethod
    def reload_config(cls):
        """强制重新加载配置"""
        from app.settings import settings
        cls._config_cache = JsonConfigLoader.reload(settings.device_protocol_data_path)

    @classmethod
    def match_by_model(cls, device_model: str) -> Optional[DeviceMatchResult]:
        """根据设备型号匹配，返回含置信度的结果"""
        config = cls._load_config()
        entries = config.get("entries", {})
        model_lower = device_model.lower()

        for key, info in entries.items():
            if key in model_lower:
                return DeviceMatchResult(
                    device_type=info["type"],
                    device_model=device_model,
                    vendor=info.get("vendor", ""),
                    recommended_protocol=info.get("protocol", ""),
                    match_confidence=95.0,
                    match_source="model",
                )
        return None

    @classmethod
    def match_by_log_sample(cls, log_line: str) -> Optional[DeviceMatchResult]:
        """根据日志样例推断设备类型（从 collect_templates.json 加载特征关键词）"""
        config = cls._load_config()
        log_features = config.get("log_features", {})

        # 也从 collect_templates.json 加载特征
        from app.settings import settings
        templates_config = JsonConfigLoader.get(settings.collect_template_data_path, "log_features", {})
        if templates_config:
            log_features.update(templates_config)

        log_lower = log_line.lower()

        best_match: Optional[DeviceMatchResult] = None
        best_score = 0.0

        for device_type, feature_info in log_features.items():
            keywords = feature_info.get("keywords", [])
            matched_count = 0
            for kw in keywords:
                if kw in log_lower:
                    matched_count += 1

            if matched_count > 0:
                # 置信度 = 匹配关键词数 / 总关键词数 * 100，上限 90
                confidence = min(matched_count / max(len(keywords), 1) * 100, 90.0)
                if confidence > best_score:
                    best_score = confidence
                    best_match = DeviceMatchResult(
                        device_type=device_type,
                        log_format="auto-detected",
                        recommended_protocol=feature_info.get("recommended_protocol", "file"),
                        match_confidence=round(confidence, 1),
                        match_source="log_sample",
                    )

        return best_match

    @classmethod
    def get_recommendation(cls, device_type: str, device_model: str = "", scale: str = "small") -> dict:
        """获取采集方案推荐 — 返回含置信度的完整结果"""
        from modules.log_collect.collect_strategy import CollectStrategyFactory

        # 优先按型号匹配
        if device_model:
            info = cls.match_by_model(device_model)
            if info:
                plan = CollectStrategyFactory.get_plan(info.device_type, device_model, scale)
                return {
                    "device_info": {
                        "type": info.device_type,
                        "model": info.device_model,
                        "vendor": info.vendor,
                    },
                    "plan": plan,
                    "match_source": info.match_source,
                    "match_confidence": info.match_confidence,
                }

        # 按设备类型匹配（置信度固定 80）
        plan = CollectStrategyFactory.get_plan(device_type, device_model, scale)
        return {
            "device_info": {
                "type": device_type,
                "model": device_model,
            },
            "plan": plan,
            "match_source": "type",
            "match_confidence": 80.0,
        }
