"""模块四：技术赋能脚本生成 — API 路由"""

from fastapi import APIRouter, Depends

from modules.script_gen.service import ScriptGenService
from modules.script_gen.schemas import (
    RegexGenReq, BatchRegexGenReq,
    ESQueryGenReq, BatchESQueryGenReq,
    TraceLinkReq,
    OptimizeReq,
    SplunkSearchReq,
    SplunkConfigSaveReq,
    ESSearchReq,
    ESConfigSaveReq,
)
from core.context_manager import ContextManager
from app.dependencies import get_context
from app.exceptions import ParamInvalidException
from common.logger import LogManager

logger = LogManager.get_logger()

router = APIRouter(prefix="/api/v1/script-gen", tags=["技术赋能脚本生成"])


@router.post("/regex")
async def generate_regex(req: RegexGenReq, ctx: ContextManager = Depends(get_context)):
    """生成正则规则"""
    result = await ScriptGenService.generate_regex(
        scenario=req.scenario,
        log_sample=req.log_sample,
        device_type=req.device_type,
        context=ctx,
    )
    return result


@router.post("/regex/batch")
async def generate_regex_batch(req: BatchRegexGenReq, ctx: ContextManager = Depends(get_context)):
    """批量生成正则规则"""
    scenarios = [s.model_dump() for s in req.scenarios]
    result = await ScriptGenService.generate_regex_batch(scenarios, context=ctx)
    return result


@router.post("/es-query")
async def generate_es_query(req: ESQueryGenReq, ctx: ContextManager = Depends(get_context)):
    """生成 ES 检索语句"""
    result = await ScriptGenService.generate_es_query(
        search_scenario=req.search_scenario,
        index_pattern=req.index_pattern,
        time_range=req.time_range,
        filters=req.filters,
        context=ctx,
    )
    return result


@router.post("/es-query/batch")
async def generate_es_query_batch(req: BatchESQueryGenReq, ctx: ContextManager = Depends(get_context)):
    """批量生成 ES 检索语句"""
    queries = [q.model_dump() for q in req.queries]
    result = await ScriptGenService.generate_es_query_batch(queries, context=ctx)
    return result


@router.post("/trace")
async def trace_attack(req: TraceLinkReq, ctx: ContextManager = Depends(get_context)):
    """攻击链路溯源"""
    result = await ScriptGenService.trace_attack(
        logs=req.logs,
        attack_type=req.attack_type,
        start_time=req.start_time,
        end_time=req.end_time,
        context=ctx,
    )
    return result


@router.post("/optimize")
async def optimize_script(req: OptimizeReq, ctx: ContextManager = Depends(get_context)):
    """脚本优化纠错"""
    result = await ScriptGenService.optimize_script(
        script=req.script,
        script_type=req.script_type,
        scenario=req.scenario,
        context=ctx,
    )
    return result


@router.post("/splunk/search")
async def splunk_search(req: SplunkSearchReq, ctx: ContextManager = Depends(get_context)):
    """执行 Splunk 搜索并返回结果"""
    result = await ScriptGenService.splunk_search(
        spl_query=req.spl_query,
        max_results=req.max_results,
        splunk_config=req.splunk_config.model_dump() if req.splunk_config else None,
        context=ctx,
    )
    return result


@router.post("/splunk/open-url")
async def splunk_open_url(req: SplunkSearchReq):
    """生成 Splunk Web UI 跳转链接"""
    result = await ScriptGenService.splunk_open_url(
        spl_query=req.spl_query,
        splunk_config=req.splunk_config.model_dump() if req.splunk_config else None,
    )
    return result


@router.post("/splunk/test")
async def splunk_test(req: SplunkSearchReq):
    """测试 Splunk 连接"""
    result = await ScriptGenService.splunk_test(
        spl_query=req.spl_query,
        splunk_config=req.splunk_config.model_dump() if req.splunk_config else None,
    )
    return result


@router.post("/splunk/config")
async def splunk_save_config(req: SplunkConfigSaveReq):
    """保存 Splunk 配置到 .env 文件"""
    result = await ScriptGenService.splunk_save_config(req.model_dump())
    return result


@router.post("/es/search")
async def es_search(req: ESSearchReq):
    """执行 ES 搜索并返回结果"""
    result = await ScriptGenService.es_search(
        query_dsl=req.query_dsl,
        index_pattern=req.index_pattern,
        max_results=req.max_results,
        es_config=req.es_config.model_dump() if req.es_config else None,
    )
    return result


@router.post("/es/test")
async def es_test(req: ESSearchReq):
    """测试 ES 连接"""
    result = await ScriptGenService.es_test(
        es_config=req.es_config.model_dump() if req.es_config else None,
    )
    return result


@router.post("/es/config")
async def es_save_config(req: ESConfigSaveReq):
    """保存 ES 配置到 .env 文件"""
    result = await ScriptGenService.es_save_config(req.model_dump())
    return result