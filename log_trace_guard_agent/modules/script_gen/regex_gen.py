"""模块四：正则规则生成策略 — 根据攻防场景自动生成行业标准正则"""

import re
from typing import Optional

from modules.script_gen.script_strategy import BaseScriptStrategy
from common.json_util import JsonConfigLoader
from common.logger import LogManager
from app.settings import settings

logger = LogManager.get_logger()


class RegexGenStrategy(BaseScriptStrategy):
    """正则规则生成策略 — 基于规则知识库 + 场景模板 + RAG知识库增强"""

    strategy_type = "regex"
    strategy_name = "正则规则生成"

    def __init__(self):
        self._scene_keywords = {}
        self._fallback_rules = {}
        self._load_config()

    def _load_config(self):
        """加载外部配置"""
        keywords_path = f"{settings.rule_data_dir}/script_gen_scene_keywords.json"
        all_keywords = JsonConfigLoader.load(keywords_path) or {}
        self._scene_keywords = all_keywords.get("regex", {})

        fallback_path = f"{settings.rule_data_dir}/script_gen_fallback_rules.json"
        self._fallback_rules = JsonConfigLoader.load(fallback_path) or {}

    def can_handle(self, params: dict) -> bool:
        scenario = (params.get("scenario") or "").strip()
        return bool(scenario)

    def generate(self, params: dict) -> dict:
        scenario = params.get("scenario", "")
        log_sample = params.get("log_sample")
        device_type = params.get("device_type")

        # 1. 识别攻击场景类型
        scene_type = self._identify_scene(scenario)

        # 2. 从外部配置加载规则模板
        config_path = f"{settings.rule_data_dir}/script_gen_regex.json"
        templates = JsonConfigLoader.load(config_path) or {}

        # 3. 匹配模板或生成规则
        regexes = []
        note_parts = []

        if scene_type in templates:
            for tpl in templates[scene_type]:
                rule = {
                    "name": tpl.get("name", ""),
                    "pattern": tpl.get("pattern", ""),
                    "description": tpl.get("description", ""),
                    "match_example": tpl.get("match_example"),
                    "priority": tpl.get("priority", 50),
                }
                regexes.append(rule)

        # 4. 基于日志样例微调（如有）
        if log_sample and regexes:
            for rule in regexes:
                if rule.get("match_example"):
                    pattern = rule["pattern"]
                    try:
                        if re.search(pattern, log_sample, re.IGNORECASE):
                            rule["match_example"] = log_sample[:200]
                    except re.error:
                        pass

        # 5. 兜底：无模板匹配时尝试 RAG 知识库
        if not regexes:
            regexes, rag_note = self._try_rag_fallback(scenario, scene_type)
            if rag_note:
                note_parts.append(rag_note)

        # 6. 最终兜底：使用通用规则
        if not regexes:
            regexes = self._get_fallback_rules(scene_type, scenario)

        return {
            "regexes": regexes,
            "scenario": scenario,
            "note": self._get_note(regexes, scene_type, note_parts),
        }

    def _identify_scene(self, scenario: str) -> str:
        """识别攻击场景类型 — 配置驱动"""
        scenario_lower = scenario.lower()
        scores = {}
        for scene_type, keywords in self._scene_keywords.items():
            score = sum(2 if kw in scenario_lower else 0 for kw in keywords)
            if score > 0:
                scores[scene_type] = score
        if scores:
            return max(scores, key=scores.get)
        return "unknown"

    def _try_rag_fallback(self, scenario: str, scene_type: str) -> tuple[list, Optional[str]]:
        """尝试通过 RAG 知识库检索获取规则"""
        try:
            from core.ai_base.rag_factory import RAGFactory
            import asyncio

            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 在同步上下文中创建新任务
                try:
                    rag = RAGFactory.get_rag("scripts")
                    if rag:
                        results = rag.search(query=scenario, top_k=3)
                        if results:
                            rules = []
                            for r in results:
                                rules.append({
                                    "name": f"知识库推荐: {r.get('title', '规则')}",
                                    "pattern": r.get("content", ""),
                                    "description": r.get("description", "来自知识库的规则推荐"),
                                    "match_example": r.get("example"),
                                    "priority": 60,
                                })
                            return rules, "已检索知识库相关规则，建议人工验证后使用。"
                except Exception as e:
                    logger.warning(f"RAG检索失败: {e}")
                    return [], "RAG知识库检索异常，已降级为规则层结果。"
        except ImportError:
            logger.debug("RAGFactory 未就绪，跳过知识库检索")
        return [], None

    def _get_fallback_rules(self, scene_type: str, scenario: str) -> list[dict]:
        """兜底规则生成 — 从外部配置加载"""
        # 先尝试匹配场景类型的兜底规则
        specific = self._fallback_rules.get(scene_type)
        if specific:
            return specific

        # 使用通用兜底
        default = self._fallback_rules.get("default", [])
        if default:
            import copy
            rules = copy.deepcopy(default)
            for rule in rules:
                if "pattern_template" in rule:
                    escaped = re.escape(scenario[:50])
                    rule["pattern"] = rule["pattern_template"].format(scenario_escaped=escaped)
                    rule["description"] = f"基于场景「{scenario[:50]}」的通用检测规则，建议补充日志样例后优化"
                    rule.pop("pattern_template", None)
            return rules

        return [{
            "name": "通用规则",
            "pattern": rf"(?i){re.escape(scenario[:50])}",
            "description": f"基于场景「{scenario[:50]}」的通用检测规则",
            "match_example": None,
            "priority": 50,
        }]

    def _get_note(self, regexes: list, scene_type: str, extra_notes: list = None) -> Optional[str]:
        """生成附加说明"""
        notes = extra_notes or []
        if not regexes:
            notes.append("未匹配到已知攻击场景，建议补充日志样例后重新生成。")
        if scene_type == "unknown":
            notes.append("场景类型未明确识别，已生成通用规则，建议细化场景描述。")
        if not notes:
            return None
        return "；".join(notes)