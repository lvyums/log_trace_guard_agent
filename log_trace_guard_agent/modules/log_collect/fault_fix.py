"""采集故障智能排错 — 外部知识库驱动 + 多维度联合诊断"""

from dataclasses import dataclass, field
from typing import Optional

from common.logger import LogManager
from common.json_util import JsonConfigLoader

logger = LogManager.get_logger()


@dataclass
class FaultDiagnosis:
    """故障诊断结果"""
    fault_type: str
    fault_desc: str
    severity: str = "medium"  # high / medium / low
    match_score: float = 0.0  # 匹配置信度 0~100
    possible_causes: list[str] = field(default_factory=list)
    fix_steps: list[str] = field(default_factory=list)
    prevention: list[str] = field(default_factory=list)


class FaultFixer:
    """故障诊断器 — 外部知识库驱动，支持多维度联合匹配"""

    _kb_cache: Optional[dict] = None

    @classmethod
    def _load_kb(cls) -> dict:
        """加载故障知识库"""
        if cls._kb_cache is None:
            from app.settings import settings
            cls._kb_cache = JsonConfigLoader.load(settings.fault_kb_data_path)
        return cls._kb_cache or {}

    @classmethod
    def reload_kb(cls):
        """强制重新加载知识库"""
        from app.settings import settings
        cls._kb_cache = JsonConfigLoader.reload(settings.fault_kb_data_path)

    @classmethod
    def diagnose(
        cls,
        symptom: str,
        protocol: Optional[str] = None,
        device_type: Optional[str] = None,
        error_log: Optional[str] = None,
    ) -> Optional[FaultDiagnosis]:
        """多维度联合诊断 — 支持症状描述、传输协议、设备类型、原始报错日志

        Args:
            symptom: 故障症状描述
            protocol: 传输协议（syslog/file/agent 等）
            device_type: 设备类型
            error_log: 原始报错日志片段
        """
        kb = cls._load_kb()
        entries = kb.get("entries", {})

        # 合并所有诊断输入为一个搜索文本
        search_text = symptom.lower()
        if protocol:
            search_text += f" {protocol}"
        if device_type:
            search_text += f" {device_type}"
        if error_log:
            search_text += f" {error_log.lower()}"

        best_match: Optional[FaultDiagnosis] = None
        best_score = 0.0

        for fault_key, fault_data in entries.items():
            score = cls._calculate_match_score(search_text, fault_data)
            if score > best_score:
                best_score = score
                best_match = FaultDiagnosis(
                    fault_type=fault_data["fault_type"],
                    fault_desc=fault_data["fault_desc"],
                    severity=fault_data.get("severity", "medium"),
                    match_score=round(score, 1),
                    possible_causes=fault_data.get("possible_causes", []),
                    fix_steps=fault_data.get("fix_steps", []),
                    prevention=fault_data.get("prevention", []),
                )

        if best_match and best_match.match_score > 20:
            return best_match
        return None

    @classmethod
    def _calculate_match_score(cls, search_text: str, fault_data: dict) -> float:
        """计算故障匹配分数"""
        score = 0.0

        # 1. 关键词匹配（主要权重）
        keywords = fault_data.get("keywords", [])
        matched_keywords = sum(1 for kw in keywords if kw in search_text)
        if keywords:
            score += (matched_keywords / len(keywords)) * 60  # 最高60分

        # 2. 传输协议匹配（加分项）
        protocol_hints = fault_data.get("protocol_hints", [])
        if protocol_hints:
            for hint in protocol_hints:
                if hint in search_text:
                    score += 20
                    break

        # 3. 故障类型名称直接匹配（高权重）
        fault_type = fault_data.get("fault_type", "")
        if fault_type in search_text:
            score += 30

        return min(score, 100.0)

    @classmethod
    def get_all_faults(cls) -> list[dict]:
        """获取所有故障类型列表"""
        kb = cls._load_kb()
        entries = kb.get("entries", {})
        return [
            {
                "fault_key": key,
                "fault_type": data["fault_type"],
                "fault_desc": data["fault_desc"],
                "severity": data.get("severity", "medium"),
            }
            for key, data in entries.items()
        ]

    @classmethod
    def get_fault_detail(cls, fault_type: str) -> Optional[FaultDiagnosis]:
        """获取指定故障类型的详细诊断信息"""
        kb = cls._load_kb()
        entries = kb.get("entries", {})

        for fault_key, data in entries.items():
            if data["fault_type"] == fault_type:
                return FaultDiagnosis(
                    fault_type=data["fault_type"],
                    fault_desc=data["fault_desc"],
                    severity=data.get("severity", "medium"),
                    match_score=100.0,
                    possible_causes=data.get("possible_causes", []),
                    fix_steps=data.get("fix_steps", []),
                    prevention=data.get("prevention", []),
                )
        return None
