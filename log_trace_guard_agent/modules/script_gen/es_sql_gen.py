"""模块四：ES/SQL 检索语句生成策略 — 根据场景生成 ES Query DSL / SQL 语句"""

import json
from typing import Optional

from modules.script_gen.script_strategy import BaseScriptStrategy
from common.json_util import JsonConfigLoader
from app.settings import settings


class ESQueryGenStrategy(BaseScriptStrategy):
    """ES 检索语句生成策略 — 基于场景模板 + 配置化"""

    strategy_type = "es_query"
    strategy_name = "ES检索语句生成"

    SCENE_KEYWORDS = {
        "ssh_brute": ["ssh", "爆破", "brute", "登录失败", "failed password"],
        "sql_injection": ["sql注入", "sqli", "union", "select", "注入"],
        "web_attack": ["web", "http", "攻击", "scan", "扫描", "xss", "csrf"],
        "abnormal_traffic": ["异常流量", "ddos", "flood", "大量", "带宽"],
        "data_exfil": ["数据泄露", "导出", "外传", "exfil", "data"],
        "lateral_move": ["横向移动", "内网", "psexec", "wmiexec"],
    }

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
        if scene_type in templates:
            tpl = templates[scene_type]
            query = self._build_query(tpl, index_pattern, time_range, filters)
            explanation = tpl.get("explanation", f"基于场景「{scenario}」的ES检索语句")
        else:
            query = self._build_fallback_query(scenario, index_pattern, time_range)
            explanation = f"通用检索：基于场景「{scenario}」的全文检索"

        return {
            "query": json.dumps(query, ensure_ascii=False, indent=2) if isinstance(query, dict) else query,
            "explanation": explanation,
            "scenario": scenario,
            "index_pattern": index_pattern,
            "note": self._get_note(scene_type),
        }

    def _identify_scene(self, scenario: str) -> str:
        scenario_lower = scenario.lower()
        scores = {}
        for scene_type, keywords in self.SCENE_KEYWORDS.items():
            score = sum(2 if kw in scenario_lower else 0 for kw in keywords)
            if score > 0:
                scores[scene_type] = score
        return max(scores, key=scores.get) if scores else "unknown"

    def _build_query(self, tpl: dict, index_pattern: str, time_range: str, filters: dict) -> dict:
        """根据模板构建 ES Query DSL"""
        query = tpl.get("query_template", {
            "bool": {"must": [{"match": {"message": "__SCENARIO__"}}]}
        })

        # 替换场景描述
        query_str = json.dumps(query)
        query_str = query_str.replace("__SCENARIO__", tpl.get("scene_label", "unknown"))
        query = json.loads(query_str)

        # 添加时间范围过滤
        if time_range != "all":
            time_filter = self._build_time_filter(time_range)
            if "bool" in query:
                if "filter" not in query["bool"]:
                    query["bool"]["filter"] = []
                query["bool"]["filter"].append(time_filter)

        return query

    def _build_time_filter(self, time_range: str) -> dict:
        """构建时间范围过滤"""
        time_map = {
            "last_1h": "now-1h",
            "last_6h": "now-6h",
            "last_24h": "now-24h",
            "last_7d": "now-7d",
            "last_30d": "now-30d",
        }
        return {
            "range": {
                "@timestamp": {
                    "gte": time_map.get(time_range, "now-24h"),
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

    def _get_note(self, scene_type: str) -> Optional[str]:
        if scene_type == "unknown":
            return "场景类型未明确识别，已生成通用全文检索，建议细化场景描述获取更精准的查询。"
        return None