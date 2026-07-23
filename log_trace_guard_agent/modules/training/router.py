"""模块五：交互式攻防实训模块 — API 路由"""

import json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from typing import Optional

from modules.training.service import TrainingService
from modules.training.schemas import (
    TaskDispatchReq, SubmitAnswerReq, ReportReq,
)
from modules.training.error_analysis import ErrorAnalysis
from modules.training.check_strategy import CheckStrategyFactory
from modules.training.task_engine import TaskEngine
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


@router.post("/analyze-stream")
async def analyze_stream(req: SubmitAnswerReq):
    """流式分析 — SSE 逐 token 返回答案解析"""
    standard = TaskEngine.get_standard_answer(req.scenario_id, req.task_id)
    if not standard:
        return {"code": 400, "msg": "未找到标准答案"}

    strategy = CheckStrategyFactory.get_strategy(req.submit_type)
    if not strategy:
        return {"code": 400, "msg": "未知的提交类型"}

    check_result = await strategy.check(req.content, standard)
    task = TaskEngine.get_task(req.scenario_id, req.task_id)
    task_title = task.get("title", "") if task else ""
    task_description = task.get("description", "") if task else ""

    checks = check_result.get("checks", [])
    score = check_result.get("score", 0)
    grade = check_result.get("grade", "C")

    # 检查 LLM 配置
    from app.settings import settings
    if not settings.llm_api_key:
        async def no_llm_stream():
            yield f"data: {json.dumps({'type': 'result', 'score': score, 'grade': grade, 'checks': checks}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'token', 'text': '⚠️ LLM 未配置，无法生成详细分析。请在 .env 中设置 LLM_API_KEY。评分结果已生成。'}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
        return StreamingResponse(no_llm_stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    async def event_stream():
        # 先发送评分结果（JSON 事件）
        yield f"data: {json.dumps({'type': 'result', 'score': score, 'grade': grade, 'checks': checks}, ensure_ascii=False)}\n\n"

        # 然后流式输出分析文本
        try:
            async for token in ErrorAnalysis._llm_analyze_stream(
                task_title=task_title,
                task_description=task_description,
                submission_content=req.content,
                standard_answer=standard,
                checks=checks,
                score=score,
                grade=grade,
            ):
                if token:
                    yield f"data: {json.dumps({'type': 'token', 'text': token}, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error(f"流式分析异常: {e}")
            error_msg = f"\n\n[分析生成出错: {str(e)}]"
            yield f"data: {json.dumps({'type': 'token', 'text': error_msg}, ensure_ascii=False)}\n\n"

        yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/report")
async def generate_report(req: ReportReq, ctx: ContextManager = Depends(get_context)):
    """生成实训报告 — 薄弱项分析 + 能力提升方案"""
    result = await TrainingService.generate_report(
        student_id=req.student_id,
        scenario_id=req.scenario_id,
        context=ctx,
    )
    return result