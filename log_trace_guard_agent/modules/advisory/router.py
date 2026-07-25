"""规划咨询模块 — API 路由"""

from fastapi import APIRouter, Depends

from modules.advisory.service import AdvisoryService
from modules.advisory.schemas import (
    ArchitectureRecommendReq,
    PlatformChooseReq,
    GuideGenerateReq,
)
from core.context_manager import ContextManager
from app.dependencies import get_context
from common.logger import LogManager

logger = LogManager.get_logger()

router = APIRouter(prefix="/api/v1/advisory", tags=["规划咨询"])


@router.post("/architecture/recommend")
async def recommend_architecture(req: ArchitectureRecommendReq, ctx: ContextManager = Depends(get_context)):
    """架构推荐"""
    result = await AdvisoryService.recommend_architecture(
        device_count=req.device_count,
        daily_log_volume=req.daily_log_volume,
        budget=req.budget,
        team_skill=req.team_skill,
        context=ctx,
    )
    return result


@router.post("/platform/choose")
async def recommend_platform(req: PlatformChooseReq, ctx: ContextManager = Depends(get_context)):
    """平台选型推荐"""
    result = await AdvisoryService.recommend_platform(
        device_count=req.device_count,
        daily_log_volume=req.daily_log_volume,
        budget=req.budget,
        team_skill=req.team_skill,
        requirements=req.requirements,
        context=ctx,
    )
    return result


@router.post("/guide/generate")
async def generate_guide(req: GuideGenerateReq, ctx: ContextManager = Depends(get_context)):
    """生成指导手册"""
    result = await AdvisoryService.generate_guide(
        scale=req.scale,
        device_types=req.device_types,
        scenario=req.scenario,
        requirements=req.requirements,
        context=ctx,
    )
    return result
