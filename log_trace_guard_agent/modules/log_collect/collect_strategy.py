"""采集策略模式 — 不同设备对应独立采集方案"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CollectPlan:
    """采集方案数据结构"""
    device_type: str
    device_model: str = ""
    protocol: str = ""           # syslog / file / db_sync / agent
    architecture: str = ""       # 单机汇聚 / 分布式集群 / 云原生
    config_template: dict = field(default_factory=dict)
    steps: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


class BaseCollectStrategy(ABC):
    """采集策略基类"""

    device_type: str = "unknown"

    @abstractmethod
    def match(self, device_type: str, device_model: str = "") -> bool:
        """判断是否匹配该设备类型"""
        ...

    @abstractmethod
    def generate_plan(self, device_model: str = "", scale: str = "small") -> CollectPlan:
        """生成采集方案"""
        ...


class SyslogCollectStrategy(BaseCollectStrategy):
    """Syslog 推送采集策略 — 适用于防火墙/WAF/IDS 等网络设备"""

    device_type = "syslog"

    def match(self, device_type: str, device_model: str = "") -> bool:
        return device_type in ("firewall", "waf", "ids", "ips", "router", "switch")

    def generate_plan(self, device_model: str = "", scale: str = "small") -> CollectPlan:
        steps = [
            "1. 设备端开启 Syslog 推送功能",
            "2. 配置 Syslog 服务器地址和端口（默认 UDP 514 / TCP 514）",
            "3. 选择日志格式：RFC 3164 或 RFC 5424",
            "4. 配置日志级别和过滤规则",
            "5. 服务端配置 Syslog 接收器（rsyslog / syslog-ng）",
            "6. 配置日志解析规则和字段映射",
            "7. 验证日志接收和解析结果",
        ]

        config = {
            "protocol": "syslog",
            "port": 514,
            "transport": "udp",
            "format": "rfc3164",
            "server_config": "/etc/rsyslog.d/50-default.conf",
        }

        if scale == "large":
            config["transport"] = "tcp"
            config["tls"] = True
            steps.insert(3, "3.1 配置 TLS 加密传输")

        return CollectPlan(
            device_type=self.device_type,
            device_model=device_model,
            protocol="syslog",
            architecture="分布式集群" if scale == "large" else "单机汇聚",
            config_template=config,
            steps=steps,
            notes=["确保设备与采集服务器网络连通", "建议使用 TCP 协议保证日志不丢失"],
        )


class FileCollectStrategy(BaseCollectStrategy):
    """文件采集策略 — 适用于服务器日志/Web日志"""

    device_type = "file"

    def match(self, device_type: str, device_model: str = "") -> bool:
        return device_type in ("server", "web", "application", "nginx", "apache")

    def generate_plan(self, device_model: str = "", scale: str = "small") -> CollectPlan:
        steps = [
            "1. 确认日志文件路径和轮转策略",
            "2. 部署 Filebeat / Fluentd 采集代理",
            "3. 配置日志文件路径和采集规则",
            "4. 配置输出目标（ES / Kafka / 本地存储）",
            "5. 启动采集代理并验证日志流转",
            "6. 配置日志解析规则（Grokv2 / 正则）",
        ]

        config = {
            "protocol": "file",
            "log_paths": ["/var/log/syslog", "/var/log/nginx/access.log"],
            "collector": "filebeat",
            "multiline": True,
            "close_inactive": "5m",
        }

        if scale == "large":
            config["collector"] = "filebeat"
            config["output"] = "kafka"
            steps.append("7. 配置 Kafka 缓冲层削峰填谷")

        return CollectPlan(
            device_type=self.device_type,
            device_model=device_model,
            protocol="file",
            architecture="分布式集群" if scale == "large" else "单机汇聚",
            config_template=config,
            steps=steps,
            notes=["注意日志文件轮转导致的采集断层", "建议配置 multiline 处理堆栈日志"],
        )


class DBSyncCollectStrategy(BaseCollectStrategy):
    """数据库日志同步策略 — 适用于 MySQL/PostgreSQL 审计日志"""

    device_type = "db"

    def match(self, device_type: str, device_model: str = "") -> bool:
        return device_type in ("db", "mysql", "postgresql", "sqlserver", "oracle")

    def generate_plan(self, device_model: str = "", scale: str = "small") -> CollectPlan:
        steps = [
            "1. 开启数据库审计日志功能",
            "2. 配置审计日志输出方式（文件 / 表 / Syslog）",
            "3. 选择采集方式：直连查询 / 文件采集 / CDC",
            "4. 部署采集代理并配置连接信息",
            "5. 配置日志解析规则",
            "6. 验证审计日志完整性",
        ]

        config = {
            "protocol": "db_sync",
            "method": "file",
            "db_type": device_model or "mysql",
            "audit_log_path": "/var/log/mysql/audit.log",
        }

        return CollectPlan(
            device_type=self.device_type,
            device_model=device_model,
            protocol="db_sync",
            architecture="单机汇聚",
            config_template=config,
            steps=steps,
            notes=["确保审计日志不影响数据库性能", "建议配置审计日志独立存储路径"],
        )


class AgentCollectStrategy(BaseCollectStrategy):
    """Agent 采集策略 — 适用于堡垒机/IDS 等专用设备"""

    device_type = "agent"

    def match(self, device_type: str, device_model: str = "") -> bool:
        return device_type in ("bastion", "ids", "hids", "edr", "siem")

    def generate_plan(self, device_model: str = "", scale: str = "small") -> CollectPlan:
        steps = [
            "1. 确认设备支持的日志导出方式",
            "2. 选择采集代理类型（专用 Agent / Syslog / API）",
            "3. 安装并配置采集代理",
            "4. 配置日志转发目标",
            "5. 配置日志解析规则",
            "6. 验证日志采集完整性",
        ]

        config = {
            "protocol": "agent",
            "collector": "generic_agent",
            "forward_to": "log_server:514",
        }

        return CollectPlan(
            device_type=self.device_type,
            device_model=device_model,
            protocol="agent",
            architecture="单机汇聚",
            config_template=config,
            steps=steps,
            notes=["不同厂商设备采集方式差异较大", "建议优先使用标准 Syslog 协议"],
        )


class CollectStrategyFactory:
    """采集策略工厂 — 根据设备类型自动匹配最优采集方案"""

    _strategies: list[BaseCollectStrategy] = [
        SyslogCollectStrategy(),
        FileCollectStrategy(),
        DBSyncCollectStrategy(),
        AgentCollectStrategy(),
    ]

    @classmethod
    def get_strategy(cls, device_type: str) -> Optional[BaseCollectStrategy]:
        """根据设备类型返回匹配的采集策略"""
        for strategy in cls._strategies:
            if strategy.match(device_type):
                return strategy
        return None

    @classmethod
    def get_plan(cls, device_type: str, device_model: str = "", scale: str = "small") -> Optional[CollectPlan]:
        """根据设备类型生成采集方案"""
        strategy = cls.get_strategy(device_type)
        if strategy is None:
            return None
        return strategy.generate_plan(device_model, scale)

    @classmethod
    def register(cls, strategy: BaseCollectStrategy):
        """注册新的采集策略"""
        cls._strategies.append(strategy)

    @classmethod
    def get_supported_types(cls) -> list[str]:
        """获取所有支持的设备类型"""
        types = []
        for strategy in cls._strategies:
            # 从 match 方法的设备类型推断
            if strategy.device_type == "syslog":
                types.extend(["firewall", "waf", "ids", "ips", "router", "switch"])
            elif strategy.device_type == "file":
                types.extend(["server", "web", "application", "nginx", "apache"])
            elif strategy.device_type == "db":
                types.extend(["db", "mysql", "postgresql", "sqlserver", "oracle"])
            elif strategy.device_type == "agent":
                types.extend(["bastion", "ids", "hids", "edr", "siem"])
        return list(set(types))
