"""采集故障智能排错 — 外部知识库驱动 + 多维度联合诊断 (v2.0)"""

import re
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


@dataclass
class RankedCandidate:
    """排序候选项"""
    diagnosis: FaultDiagnosis
    score: float
    matched_keywords: list[str] = field(default_factory=list)


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
    def _extract_tokens(cls, text: str) -> set[str]:
        """提取文本中的特征词（中英文混合）
        
        对英文按空格/标点切词，对中文按字符和常见双字词切分。
        不使用外部分词库，纯正则实现。
        """
        text = text.lower().strip()
        tokens = set()

        # 1. 提取英文单词（按非字母字符切分）
        english_words = set(re.findall(r'[a-z]+', text))
        tokens.update(w for w in english_words if len(w) > 1)

        # 2. 提取中文单字和双字组合
        chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
        tokens.update(chinese_chars)
        # 双字组合
        for i in range(len(chinese_chars) - 1):
            tokens.add(chinese_chars[i] + chinese_chars[i + 1])

        # 3. 提取数字
        numbers = set(re.findall(r'\d+', text))
        tokens.update(numbers)

        return tokens

    @classmethod
    def _fuzzy_match_keyword(cls, keyword: str, text: str) -> float:
        """模糊匹配关键词，返回 0.0~1.0 的匹配度
        
        支持：
        - 完全包含（1.0）
        - 部分字符重叠（0.3~0.9）
        - 拼音/英文近似匹配
        """
        keyword = keyword.lower().strip()
        text = text.lower()

        # 完全匹配
        if keyword in text:
            return 1.0

        # 英文单词级别匹配（比如 "timeout" 和 "time out"）
        if re.match(r'^[a-z0-9_]+$', keyword):
            kw_words = set(re.findall(r'[a-z0-9]+', keyword))
            text_words = set(re.findall(r'[a-z0-9]+', text))
            overlap = kw_words & text_words
            if kw_words and overlap:
                return len(overlap) / len(kw_words) * 0.8
            return 0.0

        # 中文字符重叠度
        kw_chars = set(keyword)
        text_chars = set(text)
        if len(kw_chars) <= 2:
            return 0.0  # 太短不匹配
        overlap = len(kw_chars & text_chars)
        if overlap >= len(kw_chars) * 0.7:
            return overlap / len(kw_chars) * 0.7
        return 0.0

    @classmethod
    def diagnose(
        cls,
        symptom: str,
        protocol: Optional[str] = None,
        device_type: Optional[str] = None,
        error_log: Optional[str] = None,
    ) -> tuple[Optional[FaultDiagnosis], list[RankedCandidate]]:
        """多维度联合诊断 — 支持症状描述、传输协议、设备类型、原始报错日志

        Returns:
            (best_diagnosis, candidates): 最佳诊断和所有候选排序列表
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

        # 提取特征token
        search_tokens = cls._extract_tokens(search_text)

        candidates: list[RankedCandidate] = []

        for fault_key, fault_data in entries.items():
            score, matched = cls._calculate_match_score(search_text, search_tokens, fault_data)
            diagnosis = FaultDiagnosis(
                fault_type=fault_data["fault_type"],
                fault_desc=fault_data["fault_desc"],
                severity=fault_data.get("severity", "medium"),
                match_score=round(score, 1),
                possible_causes=fault_data.get("possible_causes", []),
                fix_steps=fault_data.get("fix_steps", []),
                prevention=fault_data.get("prevention", []),
            )
            candidates.append(RankedCandidate(
                diagnosis=diagnosis,
                score=score,
                matched_keywords=matched,
            ))

        # 按分数降序排列
        candidates.sort(key=lambda c: c.score, reverse=True)

        # 取最佳匹配（阈值放宽到 1 分，只要有一丝匹配就返回）
        best = candidates[0] if candidates else None
        if best and best.score > 1:
            return best.diagnosis, candidates[:5]
        return None, candidates[:5]

    @classmethod
    def _calculate_match_score(
        cls, search_text: str, search_tokens: set[str], fault_data: dict
    ) -> tuple[float, list[str]]:
        """计算故障匹配分数

        Returns:
            (score, matched_keywords): 总分数和匹配到的关键词列表
        """
        score = 0.0
        matched_keywords = []

        # 1. 关键词模糊匹配（主要权重，最高 50 分）
        keywords = fault_data.get("keywords", [])
        if keywords:
            for kw in keywords:
                match_ratio = cls._fuzzy_match_keyword(kw, search_text)
                if match_ratio > 0:
                    matched_keywords.append(kw)
                    score += match_ratio * (50 / len(keywords))

        # 2. 特征 Token 重叠匹配（加分项，最高 20 分）
        if keywords and search_tokens:
            all_kw_tokens = set()
            for kw in keywords:
                all_kw_tokens |= cls._extract_tokens(kw)
            overlap = search_tokens & all_kw_tokens
            # 排除单字符噪声
            meaningful_overlap = {t for t in overlap if len(t) > 1}
            if meaningful_overlap:
                score += min(len(meaningful_overlap) * 4, 20)

        # 3. 传输协议匹配（加分项，10 分）
        protocol_hints = fault_data.get("protocol_hints", [])
        if protocol_hints:
            for hint in protocol_hints:
                if hint in search_text:
                    score += 10
                    break

        # 4. 故障类型名称直接匹配（高权重，20 分）
        fault_type = fault_data.get("fault_type", "")
        if cls._fuzzy_match_keyword(fault_type, search_text) > 0.6:
            score += 20

        # 5. 设备类型匹配（加分项，10 分）
        device_types = fault_data.get("device_types", [])
        if device_types:
            for dt in device_types:
                if dt in search_text:
                    score += 10
                    break

        return min(score, 100.0), matched_keywords

    @classmethod
    def diagnose_best(
        cls,
        symptom: str,
        protocol: Optional[str] = None,
        device_type: Optional[str] = None,
        error_log: Optional[str] = None,
    ) -> Optional[FaultDiagnosis]:
        """兼容旧接口：仅返回最佳诊断"""
        best, _ = cls.diagnose(symptom, protocol, device_type, error_log)
        return best

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

    @classmethod
    async def diagnose_with_llm(
        cls,
        symptom: str,
        protocol: Optional[str] = None,
        device_type: Optional[str] = None,
        error_log: Optional[str] = None,
    ) -> Optional[FaultDiagnosis]:
        """调用大模型进行智能故障诊断（关键词匹配不足时的降级方案）"""
        from core.ai_base.llm_factory import LLMFactory

        parts = [f"【故障症状】{symptom}"]
        if protocol:
            parts.append(f"【传输协议】{protocol}")
        if device_type:
            parts.append(f"【设备类型】{device_type}")
        if error_log:
            parts.append(f"【错误日志】{error_log}")
        user_input = "\n".join(parts)

        system_prompt = """你是一个专业的IT运维故障诊断专家。请根据用户提供的故障信息，进行精准诊断。

请严格按照以下JSON格式输出，不要添加任何其他内容：
{
  "fault_type": "故障类型名称（简洁，如SSH连接失败）",
  "fault_desc": "故障详细描述（1-2句话）",
  "severity": "high|medium|low",
  "match_score": 85,
  "possible_causes": ["原因1", "原因2", "原因3"],
  "fix_steps": ["1. 第一步操作（包含实际命令）", "2. 第二步操作", "3. 第三步操作"],
  "prevention": ["建议1", "建议2"]
}

注意：
- severity 只输出 high/medium/low 之一
- match_score 输出 70~99 的整数，表示诊断置信度
- fix_steps 要具体可执行，包含实际 Linux 命令
- possible_causes 列出3~5个可能的根本原因
- 如果信息不足，在 possible_causes 中包含"信息不足，请补充更多细节"作为首条"""

        try:
            llm = await LLMFactory.get_light_llm()
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input},
            ]
            result = await llm.chat(messages, temperature=0.1, timeout=30)
            if not result["success"]:
                logger.warning(f"LLM 故障诊断失败: {result['error']}")
                return None

            import json
            content = result["content"].strip()
            # 兼容 markdown 代码块包裹
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            data = json.loads(content)

            return FaultDiagnosis(
                fault_type=data.get("fault_type", "未知故障"),
                fault_desc=data.get("fault_desc", ""),
                severity=data.get("severity", "medium"),
                match_score=float(data.get("match_score", 80)),
                possible_causes=data.get("possible_causes", ["请提供更多信息"]),
                fix_steps=data.get("fix_steps", ["建议联系技术支持"]),
                prevention=data.get("prevention", []),
            )
        except Exception as e:
            logger.error(f"LLM 故障诊断异常: {e}")
            return None
