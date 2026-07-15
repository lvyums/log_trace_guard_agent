"""模块四：技术赋能脚本生成 — 业务编排"""

from typing import Optional

from modules.script_gen.script_strategy import ScriptStrategyFactory
from modules.script_gen.regex_gen import RegexGenStrategy
from modules.script_gen.es_sql_gen import ESQueryGenStrategy
from modules.script_gen.platform_choose import PlatformChooseStrategy
from modules.script_gen.trace_link import TraceLinkStrategy
from core.context_manager import ContextManager, ModuleContext
from app.schemas.context_schema import ModuleStatus
from app.settings import settings
from common.logger import LogManager
from common.result_util import Result

logger = LogManager.get_logger()


class ScriptGenService:
    """技术赋能脚本生成 — 业务编排"""

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
    async def recommend_platform(device_count: int, daily_log_volume: str = "medium", budget: str = "medium", team_skill: str = "basic", requirements: Optional[list[str]] = None, context: Optional[ContextManager] = None) -> Result:
        """平台选型推荐"""
        strategy = ScriptStrategyFactory.get_strategy("platform")
        if not strategy:
            return Result.fail("平台选型策略未注册")

        params = {
            "device_count": device_count,
            "daily_log_volume": daily_log_volume,
            "budget": budget,
            "team_skill": team_skill,
            "requirements": requirements or [],
        }
        result = strategy.generate(params)

        if context:
            ctx = ModuleContext(
                module_id="script_gen",
                status=ModuleStatus.SUCCESS,
                input=params,
                output=result,
            )
            context.set_module_result("script_gen", ctx)

        return Result.ok(result)

    @staticmethod
    async def trace_attack(logs: list[str], attack_type: Optional[str] = None, start_time: Optional[str] = None, end_time: Optional[str] = None, context: Optional[ContextManager] = None) -> Result:
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
    async def optimize_script(script: str, script_type: str = "regex", scenario: Optional[str] = None, context: Optional[ContextManager] = None) -> Result:
        """脚本优化纠错"""
        if not script or not script.strip():
            return Result.fail("脚本内容不能为空")

        issues = []
        suggestions = []

        if script_type == "regex":
            analysis = ScriptGenService._analyze_regex(script)
            issues = analysis.get("issues", [])
            optimized = analysis.get("optimized", script)
            score = analysis.get("score", 50)
        elif script_type == "es_query":
            analysis = ScriptGenService._analyze_es_query(script)
            issues = analysis.get("issues", [])
            optimized = analysis.get("optimized", script)
            score = analysis.get("score", 50)
        else:
            issues = ["暂不支持该类型脚本优化"]
            optimized = script
            score = 50

        explanation = ScriptGenService._build_optimize_explanation(issues, script_type)

        result = {
            "original": script,
            "optimized": optimized,
            "issues": issues,
            "explanation": explanation,
            "score": score,
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
        """分析正则表达式质量"""
        import re
        issues = []
        suggestions = []
        optimized = script
        score = 50

        # 检查是否为空
        if not script.strip():
            issues.append("正则表达式为空")
            score = 0
            return {"issues": issues, "optimized": script, "score": score}

        # 尝试编译
        try:
            re.compile(script)
            score += 20
        except re.error as e:
            issues.append(f"正则语法错误: {str(e)}")
            score = 10
            return {"issues": issues, "optimized": script, "score": score}

        # 安全检查
        if "(?i)" not in script and "[A-Z]" not in script:
            suggestions.append("建议添加 (?i) 大小写不敏感标志，避免漏报")
        if ".*" in script or ".+" in script:
            if len(script.split(".*")) > 3 or len(script.split(".+")) > 3:
                issues.append("包含过多 .* 或 .+，可能导致性能问题或误报")
                score -= 10
            else:
                score += 5  # 合理使用
        if "(" not in script:
            suggestions.append("建议使用捕获组 () 提取关键字段，便于后续分析")
        if "\\d" in script or "\\w" in script:
            score += 5  # 使用字符类是好习惯

        # 长度评分
        if len(script) > 200:
            issues.append("正则表达式过长，建议拆分或简化")
            score -= 10
        elif len(script) >= 10:
            score += 10

        score = max(0, min(100, score))
        return {"issues": issues + suggestions, "optimized": optimized, "score": score}

    @staticmethod
    def _analyze_es_query(script: str) -> dict:
        """分析 ES Query DSL 质量"""
        import json
        issues = []
        optimized = script
        score = 50

        try:
            query = json.loads(script)
            score += 20
        except json.JSONDecodeError as e:
            issues.append(f"JSON 格式错误: {str(e)}")
            score = 10
            return {"issues": issues, "optimized": script, "score": score}

        if not isinstance(query, dict):
            issues.append("ES Query DSL 应为 JSON 对象")
            score = 10
            return {"issues": issues, "optimized": script, "score": score}

        if "query" in query:
            score += 10
        else:
            issues.append("缺少顶级 query 字段")

        if "size" in query:
            if query.get("size", 0) > 10000:
                issues.append("size 超过 10000，建议使用滚动查询")
                score -= 10

        if "aggs" in query:
            score += 10

        score = max(0, min(100, score))
        return {"issues": issues, "optimized": optimized, "score": score}

    @staticmethod
    def _build_optimize_explanation(issues: list, script_type: str) -> str:
        """生成优化说明"""
        if not issues:
            return f"脚本质量良好，无需优化。"
        if script_type == "regex":
            return f"发现 {len(issues)} 个可优化点，建议逐一排查后优化正则表达式。"
        elif script_type == "es_query":
            return f"发现 {len(issues)} 个可优化点，建议调整后重试。"
        return f"发现 {len(issues)} 个可优化点。"