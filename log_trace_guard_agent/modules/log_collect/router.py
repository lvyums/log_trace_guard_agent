"""日志采集架构指导模块 — API 路由"""

from fastapi import APIRouter, Depends

from modules.log_collect.service import LogCollectService
from core.context_manager import ContextManager
from app.dependencies import get_context
from app.schemas.log_collect import (
    DeviceMatchReq, CollectPlanReq, BatchPlanReq,
    FaultDiagnoseReq, ArchitectureRecommendReq,
)
from common.logger import LogManager

logger = LogManager.get_logger()

router = APIRouter(prefix="/api/v1/log-collect", tags=["日志采集架构"])


@router.post("/match")
async def match_device(req: DeviceMatchReq, ctx: ContextManager = Depends(get_context)):
    """设备类型匹配 — 自动识别并推荐采集方案"""
    result = await LogCollectService.match_device(
        device_type=req.device_type,
        device_model=req.device_model,
        scale=req.scale.value,
        context=ctx,
    )
    return result


@router.post("/plan")
async def generate_plan(req: CollectPlanReq, ctx: ContextManager = Depends(get_context)):
    """生成采集方案"""
    result = await LogCollectService.generate_plan(
        device_type=req.device_type,
        device_model=req.device_model,
        scale=req.scale.value,
        include_config=req.include_config,
        context=ctx,
    )
    return result


@router.post("/plan/batch")
async def batch_generate_plans(req: BatchPlanReq, ctx: ContextManager = Depends(get_context)):
    """批量生成采集方案"""
    devices = [item.model_dump() for item in req.devices]
    result = await LogCollectService.batch_generate_plans(devices=devices, context=ctx)
    return result


@router.post("/fault/diagnose")
async def diagnose_fault(req: FaultDiagnoseReq, ctx: ContextManager = Depends(get_context)):
    """故障诊断 — 多维度联合诊断"""
    result = await LogCollectService.diagnose_fault(
        symptom=req.symptom,
        device_type=req.device_type,
        protocol=req.protocol.value if req.protocol else None,
        error_log=req.error_log,
        context=ctx,
    )
    return result


@router.get("/fault/list")
async def get_fault_list(ctx: ContextManager = Depends(get_context)):
    """获取所有故障类型列表"""
    result = await LogCollectService.get_fault_list(context=ctx)
    return result


@router.post("/architecture/recommend")
async def recommend_architecture(req: ArchitectureRecommendReq, ctx: ContextManager = Depends(get_context)):
    """架构推荐"""
    result = await LogCollectService.recommend_architecture(
        device_count=req.device_count,
        daily_log_volume=req.daily_log_volume,
        budget=req.budget,
        team_skill=req.team_skill,
        context=ctx,
    )
    return result
