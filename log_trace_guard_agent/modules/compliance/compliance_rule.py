"""模块二：合规策略抽象基类 + 工厂注册模式 + 合规标准问答策略"""

from abc import ABC, abstractmethod
from typing import Optional, Type

from common.logger import LogManager
from common.json_util import JsonConfigLoader

logger = LogManager.get_logger()


class BaseComplianceStrategy(ABC):
    """合规策略基类 — 所有合规策略继承此类"""

    strategy_type: str = "unknown"
    strategy_name: str = "unknown"

    @abstractmethod
    def execute(self, params: dict) -> dict:
        """执行策略逻辑"""
        ...

    def can_handle(self, params: dict) -> bool:
        """判断是否能处理该场景（默认返回 True）"""
        return True


class ComplianceStrategyFactory:
    """合规策略工厂 — 注册模式，零侵入扩展"""

    _strategies: dict[str, Type[BaseComplianceStrategy]] = {}

    @classmethod
    def register(cls, strategy_type: str, strategy_cls: Type[BaseComplianceStrategy]):
        """注册策略类"""
        cls._strategies[strategy_type] = strategy_cls
        logger.info(f"注册合规策略: {strategy_type} -> {strategy_cls.__name__}")

    @classmethod
    def get_strategy(cls, strategy_type: str) -> Optional[BaseComplianceStrategy]:
        """获取策略实例"""
        strategy_cls = cls._strategies.get(strategy_type)
        if strategy_cls:
            return strategy_cls()
        return None

    @classmethod
    def get_all_types(cls) -> list[str]:
        """获取所有已注册策略类型"""
        return list(cls._strategies.keys())

    @classmethod
    def unregister(cls, strategy_type: str):
        """注销策略（用于测试）"""
        cls._strategies.pop(strategy_type, None)


# ── 合规标准问答策略 ──

class ComplianceQAStrategy(BaseComplianceStrategy):
    """合规标准问答 — 基于外部配置的合规知识库检索"""

    strategy_type = "qa"
    strategy_name = "合规标准问答"

    def __init__(self):
        self._standards = None

    def _load_standards(self) -> list[dict]:
        """从外部配置加载合规标准"""
        if self._standards is None:
            from app.settings import settings
            path = f"{settings.rule_data_dir}/compliance_standards.json"
            self._standards = JsonConfigLoader.load(path) or []
        return self._standards

    def execute(self, params: dict) -> dict:
        """执行合规标准问答"""
        question = params.get("question", "").lower()
        asset_type = params.get("asset_type")
        standard_filter = params.get("standard_filter")

        standards = self._load_standards()
        matched_items = []

        # 按标准筛选
        filtered = standards
        if standard_filter:
            kw = standard_filter.lower()
            filtered = [s for s in standards if kw in s.get("name", "").lower()
                        or kw in s.get("category", "").lower()]

        # 搜索匹配项
        keywords = self._extract_keywords(question)
        for std in filtered:
            for item in std.get("items", []):
                score = self._match_score(item, question, keywords, asset_type)
                if score > 0:
                    matched_items.append({
                        "standard_id": std["standard_id"],
                        "standard_name": std["name"],
                        "category": std.get("category", ""),
                        "item": item,
                        "score": score,
                    })

        # 按匹配度排序
        matched_items.sort(key=lambda x: x["score"], reverse=True)
        top_items = matched_items[:10]

        # 整理输出
        result_standards = {}
        for m in top_items:
            sid = m["standard_id"]
            if sid not in result_standards:
                result_standards[sid] = {
                    "standard_id": sid,
                    "name": m["standard_name"],
                    "category": m["category"],
                    "items": [],
                }
            result_standards[sid]["items"].append(m["item"])

        standards_list = list(result_standards.values())
        answer = self._build_answer(question, top_items, standards_list)

        return {
            "answer": answer,
            "standards": standards_list,
            "matched_count": len(top_items),
            "note": None if top_items else "未找到完全匹配的合规标准，建议提供更详细的问题描述",
        }

    def _extract_keywords(self, question: str) -> list[str]:
        """从问题提取关键词"""
        # 常用合规关键词
        common_kw = ["日志", "留存", "备份", "审计", "告警", "加密", "防篡改",
                     "等保", "网安法", "数据安全法", "合规", "时钟同步", "NTP",
                     "存储", "6个月", "半年", "1年", "实时", "监控"]
        found = []
        for kw in common_kw:
            if kw.lower() in question:
                found.append(kw.lower())
        return found

    def _match_score(self, item: dict, question: str, keywords: list[str],
                     asset_type: Optional[str] = None) -> int:
        """计算匹配得分"""
        score = 0
        text = (
            item.get("requirement", "") + " " +
            item.get("detail", "") + " " +
            item.get("risk_if_not", "")
        ).lower()

        # 关键词匹配
        for kw in keywords:
            if kw in text:
                score += 10
            if kw in question:
                score += 5

        # 资产类型匹配
        if asset_type and asset_type.lower() in [
            d.lower() for d in item.get("applicable_devices", [])
        ]:
            score += 15
        if asset_type and "all" in item.get("applicable_devices", []):
            score += 5

        # 问题关键词在 requirement 中完全匹配
        for qw in question.split():
            if len(qw) > 1 and qw in text:
                score += 3

        return score

    def _build_answer(self, question: str, top_items: list, standards: list) -> str:
        """根据匹配结果构建回答"""
        if not top_items:
            return (
                f"关于「{question}」的合规要求，当前知识库中"
                f"未找到精确匹配的标准条目。建议：\n"
                f"1. 使用更具体的关键词（如：等保三级、日志留存、审计频率）\n"
                f"2. 指定资产类型（如：防火墙、数据库、服务器）\n"
                f"3. 参考以下常见合规场景：日志留存不少于6个月、审计记录定期备份、"
                f"时钟同步、实时告警"
            )

        categories = set(s["category"] for s in standards)
        answer = (
            f"根据{'、'.join(categories)}要求，关于您的问题，以下是相关合规标准：\n\n"
        )

        for i, m in enumerate(top_items[:5], 1):
            item = m["item"]
            answer += (
                f"{i}. {item['requirement']}\n"
                f"   {item['detail']}\n"
                f"   检查方法：{item['check_method']}\n"
                f"   不符合风险：{item['risk_if_not']}\n\n"
            )

        answer += (
            f"共找到 {len(top_items)} 条相关合规标准条目，"
            f"涉及 {len(standards)} 份标准文件。"
        )
        return answer