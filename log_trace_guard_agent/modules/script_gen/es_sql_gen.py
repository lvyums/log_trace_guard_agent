"""模块四：ES/SQL 检索语句生成策略 — 根据场景生成 ES Query DSL / SQL 语句"""

import json
from typing import Optional

from modules.script_gen.script_strategy import BaseScriptStrategy
from common.json_util import JsonConfigLoader
from common.logger import LogManager
from app.settings import settings

logger = LogManager.get_logger()


class ESQueryGenStrategy(BaseScriptStrategy):
    """ES 检索语句生成策略 — 基于场景模板 + 配置化 + RAG知识库增强"""

    strategy_type = "es_query"
    strategy_name = "ES检索语句生成"

    def __init__(self):
        self._scene_keywords = {}
        self._time_map = {}
        self._load_config()

    def _load_config(self):
        """加载外部配置"""
        keywords_path = f"{settings.rule_data_dir}/script_gen_scene_keywords.json"
        all_keywords = JsonConfigLoader.load(keywords_path) or {}
        self._scene_keywords = all_keywords.get("es_query", {})

        time_path = f"{settings.rule_data_dir}/script_gen_time_map.json"
        self._time_map = JsonConfigLoader.load(time_path) or {}

    def can_handle(self, params: dict) -> bool:
        return bool(params.get("search_scenario"))

    def generate(self, params: dict) -> dict:
        scenario = params.get("search_scenario", "")
        index_pattern = params.get("index_pattern", "logs-*")
        time_range = params.get("time_range", "last_24h")
        filters = params.get("filters", {})

        # 1. 识别场景
        scene_type = self._identify_scene(scenario)

        # 2. 从外部配置加载模板
        config_path = f"{settings.rule_data_dir}/script_gen_es_queries.json"
        templates = JsonConfigLoader.load(config_path) or {}

        # 3. 生成查询
        query = None
        explanation = ""
        note_parts = []

        if scene_type in templates:
            tpl = templates[scene_type]
            query = self._build_query(tpl, index_pattern, time_range, filters)
            explanation = tpl.get("explanation", f"基于场景「{scenario}」的ES检索语句")
        else:
            # 尝试 RAG 知识库
            query, explanation, rag_note = self._try_rag_fallback(scenario, index_pattern, time_range)
            if rag_note:
                note_parts.append(rag_note)

        if query is None:
            query = self._build_fallback_query(scenario, index_pattern, time_range)
            explanation = f"通用检索：基于场景「{scenario}」的全文检索"

        return {
            "query": json.dumps(query, ensure_ascii=False, indent=2) if isinstance(query, dict) else query,
            "explanation": explanation,
            "scenario": scenario,
            "index_pattern": index_pattern,
            "note": self._get_note(scene_type, note_parts),
        }

    def _identify_scene(self, scenario: str) -> str:
        """识别场景类型 — 配置驱动"""
        scenario_lower = scenario.lower()
        scores = {}
        for scene_type, keywords in self._scene_keywords.items():
            score = sum(2 if kw in scenario_lower else 0 for kw in keywords)
            if score > 0:
                scores[scene_type] = score
        return max(scores, key=scores.get) if scores else "unknown"

    def _try_rag_fallback(self, scenario: str, index_pattern: str, time_range: str) -> tuple:
        """尝试通过 RAG 知识库检索获取查询模板"""
        try:
            from core.ai_base.rag_factory import RAGFactory

            kb = RAGFactory.get_kb("scripts")
            if kb:
                results = kb.retrieve(query=scenario, top_k=3).items
                if results:
                    # 使用知识库结果构建查询
                    must_conditions = []
                    for r in results:
                        content = r.get("content", "")
                        if content:
                            must_conditions.append({"match": {"message": content[:100]}})

                    if must_conditions:
                        query = {
                            "bool": {
                                "must": must_conditions,
                                "filter": [self._build_time_filter(time_range)] if time_range != "all" else [],
                            }
                        }
                        return query, f"基于知识库检索：场景「{scenario}」", "已检索知识库相关查询模式，建议验证后使用。"
        except Exception as e:
            logger.warning(f"ES查询RAG检索失败: {e}")
            return None, "", "RAG知识库检索异常，已降级为规则层结果。"
        return None, "", None

    def _build_query(self, tpl: dict, index_pattern: str, time_range: str, filters: dict) -> dict:
        """根据模板构建 ES Query DSL"""
        query = tpl.get("query_template", {
            "bool": {"must": [{"match": {"message": "__SCENARIO__"}}]}
        })

        # 替换场景描述
        query_str = json.dumps(query)
        query_str = query_str.replace("__SCENARIO__", tpl.get("scene_label", "unknown"))
        query = json.loads(query_str)

        # 添加时间范围过滤 — 兼容 {query: {bool: ...}} 和 {bool: ...} 两种结构
        if time_range != "all":
            time_filter = self._build_time_filter(time_range)
            # 找到 bool 所在的层级
            bool_part = query.get("query", {}).get("bool") or query.get("bool")
            if bool_part is not None:
                if "filter" not in bool_part:
                    bool_part["filter"] = []
                bool_part["filter"].append(time_filter)

        return query

    def _build_time_filter(self, time_range: str) -> dict:
        """构建时间范围过滤 — 配置驱动"""
        gte = self._time_map.get(time_range) or self._time_map.get("default", "now-24h")
        return {
            "range": {
                "@timestamp": {
                    "gte": gte,
                    "lte": "now",
                }
            }
        }

    def _build_fallback_query(self, scenario: str, index_pattern: str, time_range: str) -> dict:
        """兜底查询"""
        query = {
            "bool": {
                "must": [
                    {"match": {"message": scenario}}
                ],
                "filter": [
                    self._build_time_filter(time_range)
                ] if time_range != "all" else []
            }
        }
        return query

    def _get_note(self, scene_type: str, extra_notes: list = None) -> Optional[str]:
        """生成附加说明"""
        notes = extra_notes or []
        if scene_type == "unknown":
            notes.append("场景类型未明确识别，已生成通用全文检索，建议细化场景描述获取更精准的查询。")
        if not notes:
            return None
        return "；".join(notes)