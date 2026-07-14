"""设备类型匹配 — 根据设备型号/日志样例自动匹配最优采集方案"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class DeviceInfo:
    """设备信息"""
    device_type: str        # 防火墙/WAF/服务器/数据库
    device_model: str = ""  # 具体型号
    vendor: str = ""        # 厂商
    log_format: str = ""    # 日志格式
    recommended_protocol: str = ""  # 推荐采集协议


# 设备型号 → 采集协议映射表
DEVICE_PROTOCOL_MAP = {
    # 防火墙
    "paloalto": {"type": "firewall", "vendor": "Palo Alto", "protocol": "syslog"},
    "fortigate": {"type": "firewall", "vendor": "Fortinet", "protocol": "syslog"},
    "usg": {"type": "firewall", "vendor": "Huawei", "protocol": "syslog"},
    "asa": {"type": "firewall", "vendor": "Cisco", "protocol": "syslog"},
    "iptables": {"type": "firewall", "vendor": "Linux", "protocol": "syslog"},

    # WAF
    "modsecurity": {"type": "waf", "vendor": "Apache", "protocol": "file"},
    "yundun": {"type": "waf", "vendor": "Yundun", "protocol": "syslog"},
    "anquanbao": {"type": "waf", "vendor": "Anquanbao", "protocol": "syslog"},

    # 服务器
    "linux": {"type": "server", "vendor": "Linux", "protocol": "file"},
    "windows": {"type": "server", "vendor": "Microsoft", "protocol": "agent"},

    # 数据库
    "mysql": {"type": "db", "vendor": "Oracle", "protocol": "file"},
    "postgresql": {"type": "db", "vendor": "PostgreSQL", "protocol": "file"},
    "sqlserver": {"type": "db", "vendor": "Microsoft", "protocol": "agent"},
    "oracle": {"type": "db", "vendor": "Oracle", "protocol": "agent"},

    # Web 服务器
    "nginx": {"type": "web", "vendor": "Nginx", "protocol": "file"},
    "apache": {"type": "web", "vendor": "Apache", "protocol": "file"},
    "iis": {"type": "web", "vendor": "Microsoft", "protocol": "agent"},
}


class DeviceMatcher:
    """设备类型匹配器 — 根据设备型号/厂商自动识别并推荐采集方案"""

    @classmethod
    def match_by_model(cls, device_model: str) -> Optional[DeviceInfo]:
        """根据设备型号匹配"""
        model_lower = device_model.lower()
        for key, info in DEVICE_PROTOCOL_MAP.items():
            if key in model_lower:
                return DeviceInfo(
                    device_type=info["type"],
                    device_model=device_model,
                    vendor=info["vendor"],
                    recommended_protocol=info["protocol"],
                )
        return None

    @classmethod
    def match_by_log_sample(cls, log_line: str) -> Optional[DeviceInfo]:
        """根据日志样例推断设备类型"""
        log_lower = log_line.lower()

        # 按特征关键词匹配
        features = {
            "firewall": ["ufw", "pf:", "kernel:", "iptables", "firewall", "deny.*src=", "block.*from"],
            "waf": ["waf", "attack detected", "modsecurity", "violation", "blocked.*attack"],
            "server": ["sshd", "sudo", "systemd", "cron"],
            "db": ["mysql", "postgresql", "query", "select", "insert", "connection received"],
            "web": ["http/1.", "get /", "post /", "mozilla", "nginx", "apache"],
        }

        for device_type, keywords in features.items():
            for kw in keywords:
                if kw in log_lower:
                    return DeviceInfo(
                        device_type=device_type,
                        log_format="auto-detected",
                        recommended_protocol="syslog" if device_type in ("firewall", "waf") else "file",
                    )

        return None

    @classmethod
    def get_recommendation(cls, device_type: str, device_model: str = "", scale: str = "small") -> dict:
        """获取采集方案推荐"""
        from modules.log_collect.collect_strategy import CollectStrategyFactory

        # 先尝试按型号匹配
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
                    "match_source": "model",
                }

        # 按设备类型匹配
        plan = CollectStrategyFactory.get_plan(device_type, device_model, scale)
        return {
            "device_info": {
                "type": device_type,
                "model": device_model,
            },
            "plan": plan,
            "match_source": "type",
        }
