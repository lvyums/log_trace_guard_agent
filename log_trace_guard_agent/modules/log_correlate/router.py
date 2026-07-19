"""日志联合审查 — API 路由"""

from fastapi import APIRouter, Depends

from modules.log_correlate.service import LogCorrelateService
from core.context_manager import ContextManager
from app.dependencies import get_context
from app.schemas.log_correlate import CorrelateLogsReq
from common.logger import LogManager

logger = LogManager.get_logger()

router = APIRouter(prefix="/api/v1/log-correlate", tags=["日志联合审查"])


@router.post("/correlate")
async def correlate_logs(req: CorrelateLogsReq, ctx: ContextManager = Depends(get_context)):
    """多源日志关联分析 — 检测攻击链"""
    result = await LogCorrelateService.correlate_logs(
        log_lines=req.log_lines,
        context=ctx,
        time_window_minutes=req.time_window_minutes,
        detailed=req.detailed,
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