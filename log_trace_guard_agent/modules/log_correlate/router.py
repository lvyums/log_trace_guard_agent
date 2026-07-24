"""日志联合审查 — API 路由"""

from fastapi import APIRouter, Depends

from modules.log_correlate.service import LogCorrelateService
from core.context_manager import ContextManager
from app.dependencies import get_context
from app.schemas.log_correlate import (
    CorrelateLogsReq,
    FileCrunchReq,
    ToTraceReq,
    ToScenarioReq,
)
from common.logger import LogManager

logger = LogManager.get_logger()

router = APIRouter(prefix="/api/v1/log-correlate", tags=["日志联合审查"])


@router.post("/correlate")
async def correlate_logs(req: CorrelateLogsReq, ctx: ContextManager = Depends(get_context)):
    """多源日志关联分析 — 检测攻击链（关键词 + LLM 双引擎）"""
    result = await LogCorrelateService.correlate_logs(
        log_lines=req.log_lines,
        context=ctx,
        time_window_minutes=req.time_window_minutes,
        use_llm=req.use_llm,
        detailed=req.detailed,
    )
    return result


@router.post("/file-crunch")
async def crunch_file(req: FileCrunchReq, ctx: ContextManager = Depends(get_context)):
    """上传日志文件进行关联分析"""
    result = await LogCorrelateService.crunch_file(
        file_path=req.file_path,
        file_content=req.file_content,
        time_window_minutes=req.time_window_minutes,
        use_llm=req.use_llm,
    )
    return result


@router.post("/to-trace")
async def to_trace(req: ToTraceReq, ctx: ContextManager = Depends(get_context)):
    """攻击链结果 → 生成攻击溯源脚本"""
    result = await LogCorrelateService.to_trace_script(
        log_lines=req.log_lines,
        chain_name=req.chain_name,
        attack_type=req.attack_type,
        context=ctx,
    )
    return result


@router.post("/to-scenario")
async def to_scenario(req: ToScenarioReq, ctx: ContextManager = Depends(get_context)):
    """攻击链结果 → 下发实训场景"""
    result = await LogCorrelateService.to_training_scenario(
        log_lines=req.log_lines,
        chain_name=req.chain_name,
        chain_description=req.chain_description,
        context=ctx,
    )
    return result


@router.get("/patterns")
async def list_patterns():
    """获取所有可检测的攻击链模式列表"""
    patterns = LogCorrelateService.get_available_patterns()
    return {
        "code": 0,
        "msg": "success",
        "data": {"patterns": patterns},
    }
