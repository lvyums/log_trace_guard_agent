"""模块五：交互式攻防实训模块 — API 路由"""

from fastapi import APIRouter, Depends
from typing import Optional

from modules.training.service import TrainingService
from modules.training.schemas import (
    TaskDispatchReq, SubmitAnswerReq, ReportReq,
)
from core.context_manager import ContextManager
from app.dependencies import get_context
from common.logger import LogManager

logger = LogManager.get_logger()

router = APIRouter(prefix="/api/v1/training", tags=["交互式攻防实训"])


@router.post("/dispatch")
async def dispatch_tasks(req: TaskDispatchReq, ctx: ContextManager = Depends(get_context)):
    """下发实训任务 — 获取场景列表和任务详情"""
    result = await TrainingService.dispatch_tasks(
        scenario_id=req.scenario_id,
        category=req.category,
        context=ctx,
    )
    return result


@router.post("/submit")
async def submit_answer(req: SubmitAnswerReq, ctx: ContextManager = Depends(get_context)):
    """提交实训答案 — 双维度智能校验 + 原理讲解"""
    result = await TrainingService.submit_answer(
        scenario_id=req.scenario_id,
        task_id=req.task_id,
        submit_type=req.submit_type,
        content=req.content,
        student_id=req.student_id,
        context=ctx,
    )
    return result


@router.post("/report")
async def generate_report(req: ReportReq, ctx: ContextManager = Depends(get_context)):
    """生成实训报告 — 薄弱项分析 + 能力提升方案"""
    result = await TrainingService.generate_report(
        student_id=req.student_id,
        scenario_id=req.scenario_id,
        context=ctx,
    )
    return result