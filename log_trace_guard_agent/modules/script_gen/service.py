"""模块四：技术赋能脚本生成 — 业务编排"""

import json
import re
from typing import Optional

from common.splunk_client import SplunkClient
from modules.script_gen.script_strategy import ScriptStrategyFactory
from core.context_manager import ContextManager, ModuleContext
from app.schemas.context_schema import ModuleStatus
from app.settings import settings
from common.json_util import JsonConfigLoader
from common.logger import LogManager
from common.result_util import Result

logger = LogManager.get_logger()


class ScriptGenService:
    """技术赋能脚本生成 — 业务编排"""

    _scoring_config = None

    @classmethod
    def _get_scoring_config(cls, script_type: str) -> dict:
        """获取评分阈值配置 — 从外部配置加载"""
        if cls._scoring_config is None:
            path = f"{settings.rule_data_dir}/script_gen_scoring.json"
            cls._scoring_config = JsonConfigLoader.load(path) or {}
        return cls._scoring_config.get(script_type, {})

    @staticmethod
    async def generate_regex(scenario: str, log_sample: Optional[str] = None, device_type: Optional[str] = None, context: Optional[ContextManager] = None) -> Result:
        """生成正则规则"""
        strategy = ScriptStrategyFactory.get_strategy("regex")
        if not strategy:
            return Result.fail("正则生成策略未注册")

        params = {
            "scenario": scenario,
            "log_sample": log_sample,
            "device_type": device_type,
        }
        result = strategy.generate(params)

        if context:
            ctx = ModuleContext(
                module_id="script_gen",
                status=ModuleStatus.SUCCESS if result.get("regexes") else ModuleStatus.WARNING,
                input=params,
                output=result,
            )
            context.set_module_result("script_gen", ctx)

        return Result.ok(result)

    @staticmethod
    async def generate_regex_batch(scenarios: list[dict], context: Optional[ContextManager] = None) -> Result:
        """批量生成正则规则"""
        items = []
        for i, req in enumerate(scenarios):
            result = await ScriptGenService.generate_regex(
                scenario=req.get("scenario", ""),
                log_sample=req.get("log_sample"),
                device_type=req.get("device_type"),
                context=context,
            )
            items.append({
                "index": i,
                "scenario": req.get("scenario", ""),
                "result": result.get("data") if result["code"] == 0 else None,
                "error": None if result["code"] == 0 else result["msg"],
            })

        return Result.ok({
            "total": len(scenarios),
            "success_count": sum(1 for i in items if i["result"]),
            "fail_count": sum(1 for i in items if i["error"]),
            "items": items,
        })

    @staticmethod
    async def generate_es_query(search_scenario: str, index_pattern: Optional[str] = None, time_range: Optional[str] = None, filters: Optional[dict] = None, context: Optional[ContextManager] = None) -> Result:
        """生成 ES 检索语句"""
        strategy = ScriptStrategyFactory.get_strategy("es_query")
        if not strategy:
            return Result.fail("ES检索语句生成策略未注册")

        params = {
            "search_scenario": search_scenario,
            "index_pattern": index_pattern,
            "time_range": time_range,
            "filters": filters,
        }
        result = strategy.generate(params)

        if context:
            ctx = ModuleContext(
                module_id="script_gen",
                status=ModuleStatus.SUCCESS if result.get("query") else ModuleStatus.WARNING,
                input=params,
                output=result,
            )
            context.set_module_result("script_gen", ctx)

        return Result.ok(result)

    @staticmethod
    async def generate_es_query_batch(queries: list[dict], context: Optional[ContextManager] = None) -> Result:
        """批量生成 ES 检索语句"""
        items = []
        for i, req in enumerate(queries):
            result = await ScriptGenService.generate_es_query(
                search_scenario=req.get("search_scenario", ""),
                index_pattern=req.get("index_pattern"),
                time_range=req.get("time_range"),
                filters=req.get("filters"),
                context=context,
            )
            items.append({
                "index": i,
                "scenario": req.get("search_scenario", ""),
                "result": result.get("data") if result["code"] == 0 else None,
                "error": None if result["code"] == 0 else result["msg"],
            })

        return Result.ok({
            "total": len(queries),
            "success_count": sum(1 for i in items if i["result"]),
            "fail_count": sum(1 for i in items if i["error"]),
            "items": items,
        })


    @staticmethod
    async def trace_attack(logs: list[str], attack_type: Optional[str] = None, start_time: Optional[str] = None, end_time: Optional[str] = None, pre_analyzed: Optional[dict] = None, context: Optional[ContextManager] = None) -> Result:
        """攻击链路溯源"""
        if not logs:
            return Result.fail("日志列表不能为空")
        if len(logs) > 100:
            return Result.fail("单次溯源最多支持100条日志")

        strategy = ScriptStrategyFactory.get_strategy("trace")
        if not strategy:
            return Result.fail("攻击溯源策略未注册")

        params = {
            "logs": logs,
            "attack_type": attack_type,
            "start_time": start_time,
            "end_time": end_time,
            "pre_analyzed": pre_analyzed,  # 关联分析已检出的信息，避免重复解析
        }
        result = strategy.generate(params)

        if context:
            ctx = ModuleContext(
                module_id="script_gen",
                status=ModuleStatus.SUCCESS if result.get("attack_chain") else ModuleStatus.WARNING,
                input=params,
                output=result,
            )
            context.set_module_result("script_gen", ctx)

        return Result.ok(result)

    @staticmethod
    def _get_splunk_client(config: Optional[dict] = None) -> SplunkClient:
        """获取 Splunk 客户端实例，优先使用前端传入的配置"""
        if config and config.get("base_url"):
            return SplunkClient(
                base_url=config["base_url"],
                auth_token=config.get("auth_token", ""),
                username=config.get("username", ""),
                password=config.get("password", ""),
                verify_ssl=config.get("verify_ssl", True),
            )
        return SplunkClient(
            base_url=settings.splunk_base_url,
            username=settings.splunk_username,
            password=settings.splunk_password,
            auth_token=settings.splunk_auth_token,
            verify_ssl=settings.splunk_verify_ssl,
        )

    @staticmethod
    def _has_splunk_config(config: Optional[dict] = None) -> bool:
        """检查是否有可用的 Splunk 配置"""
        if config and config.get("base_url"):
            return True
        return bool(settings.splunk_base_url)

    @staticmethod
    async def splunk_search(spl_query: str, max_results: Optional[int] = None, splunk_config: Optional[dict] = None, context: Optional[ContextManager] = None) -> Result:
        """执行 Splunk 搜索"""
        if not ScriptGenService._has_splunk_config(splunk_config):
            return Result.fail("Splunk 未配置，请在导航栏设置中配置 Splunk 连接信息")

        client = ScriptGenService._get_splunk_client(splunk_config)
        results = client.execute_search(
            spl_query=spl_query,
            max_results=max_results or settings.splunk_max_results,
            timeout=settings.splunk_search_timeout,
        )

        if results.get("error"):
            return Result.fail(results["error"])

        open_url = client.build_open_url(spl_query)
        data = {
            "results": results["results"],
            "sid": results["sid"],
            "event_count": results["event_count"],
            "open_url": open_url,
            "execution_time": results.get("execution_time", 0),
        }

        if context:
            ctx = ModuleContext(
                module_id="script_gen",
                status=ModuleStatus.SUCCESS if results["results"] else ModuleStatus.WARNING,
                input={"spl_query": spl_query},
                output=data,
            )
            context.set_module_result("script_gen", ctx)

        return Result.ok(data)

    @staticmethod
    async def splunk_open_url(spl_query: str, splunk_config: Optional[dict] = None) -> Result:
        """生成 Splunk Web UI 跳转链接"""
        if not ScriptGenService._has_splunk_config(splunk_config):
            return Result.fail("Splunk 未配置，请在导航栏设置中配置 Splunk 连接信息")

        client = ScriptGenService._get_splunk_client(splunk_config)
        url = client.build_open_url(spl_query)
        return Result.ok({"open_url": url})

    @staticmethod
    async def splunk_test(spl_query: str, splunk_config: Optional[dict] = None) -> Result:
        """测试 Splunk 连接"""
        if not splunk_config or not splunk_config.get("base_url"):
            return Result.fail("请提供 Splunk 连接配置")

        client = ScriptGenService._get_splunk_client(splunk_config)
        results = client.execute_search(
            spl_query=spl_query or "search index=_internal | head 1",
            max_results=1,
            timeout=10,
        )

        if results.get("error"):
            return Result.fail(results["error"])
        return Result.ok({"message": "Splunk 连接成功", "event_count": results.get("event_count", 0)})

    @staticmethod
    async def optimize_script(script: str, script_type: str = "regex", scenario: Optional[str] = None, context: Optional[ContextManager] = None) -> Result:
        """脚本优化纠错"""
        if not script or not script.strip():
            return Result.fail("脚本内容不能为空")

        if script_type == "regex":
            analysis = ScriptGenService._analyze_regex(script)
        elif script_type == "es_query":
            analysis = ScriptGenService._analyze_es_query(script)
        else:
            analysis = {
                "issues": ["暂不支持该类型脚本优化"],
                "optimized": script,
                "score": 50,
                "explanation": f"暂不支持 {script_type} 类型脚本优化",
            }

        explanation = ScriptGenService._build_optimize_explanation(
            analysis.get("issues", []), script_type
        )

        result = {
            "original": script,
            "optimized": analysis.get("optimized", script),
            "issues": analysis.get("issues", []),
            "explanation": explanation,
            "score": analysis.get("score", 50),
        }

        if context:
            ctx = ModuleContext(
                module_id="script_gen",
                status=ModuleStatus.SUCCESS,
                input={"script_type": script_type, "scenario": scenario},
                output=result,
            )
            context.set_module_result("script_gen", ctx)

        return Result.ok(result)

    @staticmethod
    def _analyze_regex(script: str) -> dict:
        """分析正则表达式质量 — 配置驱动评分"""
        cfg = ScriptGenService._get_scoring_config("regex")
        base_score = cfg.get("base_score", 50)
        score_min = cfg.get("score_min", 0)
        score_max = cfg.get("score_max", 100)

        issues = []
        optimized = script
        score = base_score

        # 检查是否为空
        if not script.strip():
            return {"issues": ["正则表达式为空"], "optimized": script, "score": 0}

        # 尝试编译
        try:
            re.compile(script)
            score += cfg.get("compile_pass_bonus", 20)
        except re.error as e:
            return {"issues": [f"正则语法错误: {str(e)}"], "optimized": script, "score": 10}

        # 安全检查：大小写敏感
        if "(?i)" not in script and "[A-Z]" not in script:
            suggest = cfg.get("case_insensitive_suggest", "建议添加 (?i) 大小写不敏感标志，避免漏报")
            issues.append(suggest)

        # 检查 .* 或 .+ 过度使用
        wildcard_excessive = cfg.get("wildcard_excessive_threshold", 3)
        wildcard_penalty = cfg.get("wildcard_excessive_penalty", 10)
        wildcard_bonus = cfg.get("wildcard_reasonable_bonus", 5)
        if ".*" in script or ".+" in script:
            if len(script.split(".*")) > wildcard_excessive or len(script.split(".+")) > wildcard_excessive:
                issues.append(cfg.get("wildcard_excessive_issue",
                    "包含过多 .* 或 .+，可能导致性能问题或误报"))
                score -= wildcard_penalty
            else:
                score += wildcard_bonus  # 合理使用

        # 检查捕获组
        if "(" not in script:
            issues.append(cfg.get("capture_group_suggest",
                "建议使用捕获组 () 提取关键字段，便于后续分析"))

        # 检查字符类
        if "\\d" in script or "\\w" in script:
            score += cfg.get("char_class_bonus", 5)

        # 长度评分
        length_long = cfg.get("length_long_threshold", 200)
        length_long_penalty = cfg.get("length_long_penalty", 10)
        length_min = cfg.get("length_min_threshold", 10)
        length_min_bonus = cfg.get("length_min_bonus", 10)
        if len(script) > length_long:
            issues.append(cfg.get("length_long_issue", "正则表达式过长，建议拆分或简化"))
            score -= length_long_penalty
        elif len(script) >= length_min:
            score += length_min_bonus

        score = max(score_min, min(score_max, score))
        return {"issues": issues, "optimized": optimized, "score": score}

    @staticmethod
    def _analyze_es_query(script: str) -> dict:
        """分析 ES Query DSL 质量 — 配置驱动评分"""
        cfg = ScriptGenService._get_scoring_config("es_query")
        base_score = cfg.get("base_score", 50)
        score_min = cfg.get("score_min", 0)
        score_max = cfg.get("score_max", 100)

        issues = []
        optimized = script
        score = base_score

        try:
            query = json.loads(script)
            score += cfg.get("json_parse_bonus", 20)
        except json.JSONDecodeError as e:
            return {"issues": [f"JSON 格式错误: {str(e)}"], "optimized": script, "score": 10}

        if not isinstance(query, dict):
            return {"issues": ["ES Query DSL 应为 JSON 对象"], "optimized": script, "score": 10}

        if "query" in query:
            score += cfg.get("query_field_bonus", 10)
        else:
            issues.append(cfg.get("query_field_missing_issue", "缺少顶级 query 字段"))

        size_limit = cfg.get("size_limit_threshold", 10000)
        if "size" in query and query.get("size", 0) > size_limit:
            issues.append(cfg.get("size_limit_issue",
                "size 超过 10000，建议使用滚动查询"))
            score -= cfg.get("size_limit_penalty", 10)

        if "aggs" in query:
            score += cfg.get("aggs_bonus", 10)

        score = max(score_min, min(score_max, score))
        return {"issues": issues, "optimized": optimized, "score": score}

    @staticmethod
    def _build_optimize_explanation(issues: list, script_type: str) -> str:
        """生成优化说明"""
        if not issues:
            return "脚本质量良好，无需优化。"
        if script_type == "regex":
            return f"发现 {len(issues)} 个可优化点，建议逐一排查后优化正则表达式。"
        elif script_type == "es_query":
            return f"发现 {len(issues)} 个可优化点，建议调整后重试。"
        return f"发现 {len(issues)} 个可优化点。"