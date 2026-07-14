"""采集故障智能排错 — 自动定位故障原因、输出排查步骤"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FaultDiagnosis:
    """故障诊断结果"""
    fault_type: str           # 故障类型
    fault_desc: str           # 故障描述
    possible_causes: list[str] = field(default_factory=list)  # 可能原因
    fix_steps: list[str] = field(default_factory=list)        # 修复步骤
    prevention: list[str] = field(default_factory=list)       # 预防策略
    severity: str = "medium"  # high / medium / low


# 故障知识库
FAULT_KB = {
    "log_lost": FaultDiagnosis(
        fault_type="日志丢失",
        fault_desc="采集到的日志数量明显少于设备实际产生的日志量",
        possible_causes=[
            "网络链路不稳定，UDP 传输丢包",
            "Syslog 服务端缓冲区溢出",
            "采集代理配置的过滤规则过于严格",
            "设备端日志推送功能未开启或配置错误",
            "磁盘空间不足导致日志被截断",
        ],
        fix_steps=[
            "1. 检查网络连通性: ping / traceroute 采集服务器",
            "2. 检查 Syslog 服务端状态: systemctl status rsyslog",
            "3. 查看 Syslog 缓冲区配置: /etc/rsyslog.conf 中 $WorkDirectory 和 $MainMsgQueueSize",
            "4. 检查采集代理过滤规则是否误过滤",
            "5. 确认设备端日志推送已开启",
            "6. 检查磁盘空间: df -h",
            "7. 将 UDP 改为 TCP 传输保证可靠性",
        ],
        prevention=[
            "生产环境建议使用 TCP 协议",
            "配置 Syslog 缓冲区大小 >= 10000 条",
            "定期检查磁盘空间使用率",
            "配置日志采集监控告警",
        ],
        severity="high",
    ),

    "format_error": FaultDiagnosis(
        fault_type="格式错乱",
        fault_desc="采集到的日志格式异常，无法正确解析",
        possible_causes=[
            "设备日志格式与解析规则不匹配",
            "多台设备日志格式不统一",
            "日志传输过程中编码被破坏",
            "Syslog 前缀被截断",
            "自定义日志格式未配置解析规则",
        ],
        fix_steps=[
            "1. 获取原始日志样本，确认实际格式",
            "2. 对比设备文档中的标准日志格式",
            "3. 检查解析规则配置（Grokv2 / 正则）",
            "4. 确认字符编码配置（UTF-8）",
            "5. 更新或新增解析规则",
            "6. 验证解析结果",
        ],
        prevention=[
            "统一设备日志格式标准",
            "部署前验证日志格式兼容性",
            "配置格式校验告警",
        ],
        severity="medium",
    ),

    "time_offset": FaultDiagnosis(
        fault_type="时间错位",
        fault_desc="采集到的日志时间戳与实际发生时间不一致",
        possible_causes=[
            "设备时钟未同步 NTP",
            "时区配置不一致",
            "日志传输延迟",
            "采集服务器时钟偏差",
        ],
        fix_steps=[
            "1. 检查设备 NTP 配置: ntpq -p",
            "2. 确认设备时区设置",
            "3. 检查采集服务器时钟",
            "4. 配置统一 NTP 服务器",
            "5. 同步所有设备时钟",
        ],
        prevention=[
            "所有设备配置统一 NTP 服务器",
            "定期校验时钟偏差",
            "配置时钟偏差告警阈值",
        ],
        severity="medium",
    ),

    "transport_interrupt": FaultDiagnosis(
        fault_type="传输中断",
        fault_desc="日志采集突然中断，无新日志入账",
        possible_causes=[
            "采集代理进程崩溃",
            "网络链路中断",
            "Syslog 服务端宕机",
            "防火墙策略变更阻断了采集端口",
            "设备重启后日志推送未恢复",
        ],
        fix_steps=[
            "1. 检查采集代理进程状态: ps aux | grep filebeat",
            "2. 查看采集代理日志: /var/log/filebeat/filebeat.log",
            "3. 检查网络连通性",
            "4. 检查 Syslog 服务端状态",
            "5. 检查防火墙策略: iptables -L -n",
            "6. 重启采集代理: systemctl restart filebeat",
        ],
        prevention=[
            "配置采集代理进程守护（systemd / supervisor）",
            "配置采集中断监控告警",
            "防火墙策略变更时同步更新采集端口白名单",
        ],
        severity="high",
    ),

    "入库失败": FaultDiagnosis(
        fault_type="无法入库",
        fault_desc="日志采集成功但无法写入目标存储（ES/Kafka/数据库）",
        possible_causes=[
            "目标存储服务不可用",
            "索引/Topic 不存在",
            "存储空间不足",
            "认证凭据过期",
            "字段映射与目标存储 Schema 不匹配",
        ],
        fix_steps=[
            "1. 检查目标存储服务状态",
            "2. 确认索引/Topic 是否存在",
            "3. 检查存储空间: GET _cat/indices",
            "4. 验证认证凭据有效性",
            "5. 检查字段映射配置",
            "6. 查看采集代理输出日志",
        ],
        prevention=[
            "配置存储空间监控告警",
            "定期轮转索引并清理过期数据",
            "配置认证凭据自动续期",
        ],
        severity="high",
    ),
}


class FaultFixer:
    """故障诊断器 — 根据故障症状自动定位原因并输出修复方案"""

    @classmethod
    def diagnose(cls, symptom: str) -> Optional[FaultDiagnosis]:
        """根据故障症状关键词返回诊断结果"""
        symptom_lower = symptom.lower()

        # 关键词 → 故障类型映射
        keyword_map = {
            "log_lost": ["丢失", "丢失", "日志少", "数量不对", "缺日志", "漏日志", "丢包"],
            "format_error": ["格式错", "乱码", "解析失败", "无法解析", "格式异常", "编码"],
            "time_offset": ["时间错", "时差", "时间不对", "时区", "NTP", "时间戳错"],
            "transport_interrupt": ["中断", "断开", "停止采集", "没有日志", "采集停", "进程挂"],
            "入库失败": ["入库失败", "写入失败", "ES报错", "Kafka报错", "索引失败", "存储失败"],
        }

        for fault_type, keywords in keyword_map.items():
            for kw in keywords:
                if kw in symptom_lower:
                    return FAULT_KB.get(fault_type)

        return None

    @classmethod
    def get_all_faults(cls) -> list[dict]:
        """获取所有故障类型列表"""
        return [
            {
                "fault_type": f.fault_type,
                "fault_desc": f.fault_desc,
                "severity": f.severity,
            }
            for f in FAULT_KB.values()
        ]

    @classmethod
    def get_fault_detail(cls, fault_type: str) -> Optional[FaultDiagnosis]:
        """获取指定故障类型的详细诊断信息"""
        for key, fault in FAULT_KB.items():
            if fault.fault_type == fault_type:
                return fault
        return None
