"""采集策略模式 — 工厂 + 策略模式，支持外部注册，零硬编码"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from common.logger import LogManager

logger = LogManager.get_logger()


@dataclass
class CollectPlan:
    """采集方案数据结构"""
    device_type: str
    device_model: str = ""
    protocol: str = ""           # syslog / file / db_sync / agent
    architecture: str = ""       # 单机汇聚 / 分布式集群
    config_template: dict = field(default_factory=dict)
    steps: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    rag_supplements: list[str] = field(default_factory=list)  # RAG 补充说明


class BaseCollectStrategy(ABC):
    """采集策略抽象基类 — 所有策略必须继承"""

    device_type: str = "unknown"

    @abstractmethod
    def match(self, device_type: str, device_model: str = "") -> bool:
        """判断是否匹配该设备类型"""
        ...

    @abstractmethod
    def generate_plan(self, device_model: str = "", scale: str = "small") -> CollectPlan:
        """生成采集方案"""
        ...

    def get_supported_types(self) -> list[str]:
        """返回该策略支持的设备类型列表，子类可覆盖"""
        return []


class GenericSyslogStrategy(BaseCollectStrategy):
    """通用兜底策略 — 未知设备/未知厂商时自动返回通用 Syslog 方案"""

    device_type = "generic"

    def match(self, device_type: str, device_model: str = "") -> bool:
        # 兜底策略永远返回 True，但优先级最低
        return True

    def generate_plan(self, device_model: str = "", scale: str = "small") -> CollectPlan:
        steps = [
            "1. 确认设备支持的日志导出方式",
            "2. 优先尝试 Syslog 标准协议（UDP/TCP 514）",
            "3. 如不支持 Syslog，尝试文件采集或 API 接入",
            "4. 配置日志解析规则（需手动适配格式）",
            "5. 验证日志采集完整性",
        ]

        config = {
            "protocol": "syslog",
            "port": 514,
            "transport": "udp",
            "note": "通用方案，建议根据设备实际情况调整",
        }

        return CollectPlan(
            device_type=self.device_type,
            device_model=device_model,
            protocol="syslog",
            architecture="单机汇聚",
            config_template=config,
            steps=steps,
            notes=[
                f"设备型号 [{device_model}] 未在已知设备库中匹配",
                "当前为通用采集方案，建议参考设备厂商文档确认最佳采集方式",
                "建议联系技术支持获取针对性采集方案",
            ],
        )


class SyslogCollectStrategy(BaseCollectStrategy):
    """Syslog 推送采集策略 — 适用于防火墙/WAF/IDS 等网络设备"""

    device_type = "syslog"

    _supported_types = ["firewall", "waf", "ids", "ips", "router", "switch"]

    def match(self, device_type: str, device_model: str = "") -> bool:
        return device_type in self._supported_types

    def get_supported_types(self) -> list[str]:
        return self._supported_types.copy()

    def generate_plan(self, device_model: str = "", scale: str = "small") -> CollectPlan:
        from app.settings import settings
        from common.json_util import JsonConfigLoader

        # 从外部配置加载模板
        templates = JsonConfigLoader.get(settings.collect_template_data_path, "templates.syslog", {})
        template = templates.get(scale, templates.get("small", {}))

        steps = template.get("steps", [])
        config = {k: v for k, v in template.items() if k not in ("steps", "notes")}
        notes = template.get("notes", [])

        return CollectPlan(
            device_type=self.device_type,
            device_model=device_model,
            protocol="syslog",
            architecture="分布式集群" if scale == "large" else "单机汇聚",
            config_template=config,
            steps=steps,
            notes=notes,
        )


class FileCollectStrategy(BaseCollectStrategy):
    """文件采集策略 — 适用于服务器日志/Web日志"""

    device_type = "file"

    _supported_types = ["server", "web", "application", "nginx", "apache"]

    def match(self, device_type: str, device_model: str = "") -> bool:
        return device_type in self._supported_types

    def get_supported_types(self) -> list[str]:
        return self._supported_types.copy()

    def generate_plan(self, device_model: str = "", scale: str = "small") -> CollectPlan:
        from app.settings import settings
        from common.json_util import JsonConfigLoader

        templates = JsonConfigLoader.get(settings.collect_template_data_path, "templates.file", {})
        template = templates.get(scale, templates.get("small", {}))

        steps = template.get("steps", [])
        config = {k: v for k, v in template.items() if k not in ("steps", "notes")}
        notes = template.get("notes", [])

        return CollectPlan(
            device_type=self.device_type,
            device_model=device_model,
            protocol="file",
            architecture="分布式集群" if scale == "large" else "单机汇聚",
            config_template=config,
            steps=steps,
            notes=notes,
        )


class DBSyncCollectStrategy(BaseCollectStrategy):
    """数据库日志同步策略 — 适用于 MySQL/PostgreSQL 审计日志"""

    device_type = "db"

    _supported_types = ["db", "mysql", "postgresql", "sqlserver", "oracle"]

    def match(self, device_type: str, device_model: str = "") -> bool:
        return device_type in self._supported_types

    def get_supported_types(self) -> list[str]:
        return self._supported_types.copy()

    def generate_plan(self, device_model: str = "", scale: str = "small") -> CollectPlan:
        from app.settings import settings
        from common.json_util import JsonConfigLoader

        templates = JsonConfigLoader.get(settings.collect_template_data_path, "templates.db_sync", {})
        template = templates.get("small", {})

        steps = template.get("steps", [])
        config = {k: v for k, v in template.items() if k not in ("steps", "notes")}
        config["db_type"] = device_model or "mysql"
        notes = template.get("notes", [])

        return CollectPlan(
            device_type=self.device_type,
            device_model=device_model,
            protocol="db_sync",
            architecture="单机汇聚",
            config_template=config,
            steps=steps,
            notes=notes,
        )


class AgentCollectStrategy(BaseCollectStrategy):
    """Agent 采集策略 — 适用于堡垒机/IDS 等专用设备"""

    device_type = "agent"

    _supported_types = ["bastion", "hids", "edr", "siem"]

    def match(self, device_type: str, device_model: str = "") -> bool:
        return device_type in self._supported_types

    def get_supported_types(self) -> list[str]:
        return self._supported_types.copy()

    def generate_plan(self, device_model: str = "", scale: str = "small") -> CollectPlan:
        from app.settings import settings
        from common.json_util import JsonConfigLoader

        templates = JsonConfigLoader.get(settings.collect_template_data_path, "templates.agent", {})
        template = templates.get("small", {})

        steps = template.get("steps", [])
        config = {k: v for k, v in template.items() if k not in ("steps", "notes")}
        notes = template.get("notes", [])

        return CollectPlan(
            device_type=self.device_type,
            device_model=device_model,
            protocol="agent",
            architecture="单机汇聚",
            config_template=config,
            steps=steps,
            notes=notes,
        )


class CollectStrategyFactory:
    """采集策略工厂 — 外部注册模式，工厂内部不硬编码策略实例

    使用方式:
        CollectStrategyFactory.register(SyslogCollectStrategy())
        CollectStrategyFactory.register(FileCollectStrategy())
        plan = CollectStrategyFactory.get_plan("firewall", "paloalto", "small")
    """

    _strategies: list[BaseCollectStrategy] = []
    _fallback: GenericSyslogStrategy = GenericSyslogStrategy()

    @classmethod
    def register(cls, strategy: BaseCollectStrategy):
        """注册采集策略（外部调用，禁止工厂内部实例化）"""
        cls._strategies.append(strategy)
        logger.info(f"注册采集策略: {strategy.__class__.__name__} -> {strategy.device_type}")

    @classmethod
    def get_strategy(cls, device_type: str) -> BaseCollectStrategy:
        """根据设备类型返回匹配的采集策略，无匹配返回兜底策略"""
        for strategy in cls._strategies:
            if strategy.match(device_type):
                return strategy
        logger.info(f"设备类型 [{device_type}] 未匹配已知策略，使用通用兜底方案")
        return cls._fallback

    @classmethod
    def get_plan(cls, device_type: str, device_model: str = "", scale: str = "small") -> CollectPlan:
        """根据设备类型生成采集方案，始终返回有效方案（兜底策略保证）"""
        strategy = cls.get_strategy(device_type)
        return strategy.generate_plan(device_model, scale)

    @classmethod
    def get_supported_types(cls) -> list[str]:
        """获取所有已注册策略支持的设备类型"""
        types = []
        for strategy in cls._strategies:
            types.extend(strategy.get_supported_types())
        return list(set(types))

    @classmethod
    def clear(cls):
        """清空所有已注册策略（用于测试）"""
        cls._strategies.clear()


# ── 模块加载时外部注册所有策略（不在工厂内部硬编码） ──
def _register_default_strategies():
    """注册默认采集策略"""
    CollectStrategyFactory.register(SyslogCollectStrategy())
    CollectStrategyFactory.register(FileCollectStrategy())
    CollectStrategyFactory.register(DBSyncCollectStrategy())
    CollectStrategyFactory.register(AgentCollectStrategy())


_register_default_strategies()
