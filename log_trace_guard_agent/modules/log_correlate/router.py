"""日志联合审查 — API 路由"""

import os
import uuid
from typing import List

from fastapi import APIRouter, Depends, UploadFile, File

from modules.log_correlate.service import LogCorrelateService
from core.context_manager import ContextManager
from app.dependencies import get_context
from app.schemas.log_correlate import (
    CorrelateLogsReq,
    FileCrunchReq,
    ToTraceReq,
    ToScenarioReq,
)
from app.settings import settings
from common.logger import LogManager

logger = LogManager.get_logger()

router = APIRouter(prefix="/api/v1/log-correlate", tags=["日志联合审查"])


@router.post("/correlate")
async def correlate_logs(req: CorrelateLogsReq):
    """多源日志关联分析 — 检测攻击链（关键词 + LLM 双引擎）"""
    result = await LogCorrelateService.correlate_logs(
        log_lines=req.log_lines,
        time_window_minutes=req.time_window_minutes,
        use_llm=req.use_llm,
        detailed=req.detailed,
    )
    return result


@router.post("/file-crunch")
async def crunch_file(req: FileCrunchReq):
    """上传日志文件进行关联分析（支持单文件或多文件）"""
    result = await LogCorrelateService.crunch_file(
        file_path=req.file_path,
        file_paths=req.file_paths if req.file_paths else None,
        file_content=req.file_content,
        time_window_minutes=req.time_window_minutes,
        use_llm=req.use_llm,
    )
    return result


@router.post("/cleanup")
async def cleanup_files(req: FileCrunchReq):
    """清理上传的临时文件"""
    deleted = 0
    if req.file_paths:
        for fp in req.file_paths:
            try:
                if fp.startswith(settings.upload_temp_dir) and os.path.exists(fp):
                    os.remove(fp)
                    deleted += 1
            except OSError as e:
                logger.warning(f"清理临时文件失败 {fp}: {e}")
    return {"code": 0, "msg": f"已清理 {deleted} 个文件", "data": {"deleted": deleted}}


@router.post("/to-trace")
async def to_trace(req: ToTraceReq, ctx: ContextManager = Depends(get_context)):
    """攻击链结果 → 生成攻击溯源脚本"""
    result = await LogCorrelateService.to_trace_script(
        log_lines=req.log_lines,
        chain_name=req.chain_name,
        attack_type=req.attack_type,
        pre_analyzed=req.pre_analyzed,
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


@router.post("/upload")
async def upload_files(files: List[UploadFile] = File(..., description="日志文件（支持多文件）")):
    """上传日志文件，返回保存路径供 file-crunch 使用"""
    saved_paths: list[str] = []
    os.makedirs(settings.upload_temp_dir, exist_ok=True)

    for f in files:
        content = await f.read()
        ext = os.path.splitext(f.filename or "")[1] or ".log"
        save_name = f"{uuid.uuid4().hex[:8]}_{f.filename or 'upload'}{ext}"
        save_path = os.path.join(settings.upload_temp_dir, save_name)
        with open(save_path, "wb") as out:
            out.write(content)
        saved_paths.append(save_path)
        logger.info(f"已上传文件: {f.filename} -> {save_path}")

    return {
        "code": 0,
        "msg": f"成功上传 {len(saved_paths)} 个文件",
        "data": {"file_paths": saved_paths, "count": len(saved_paths)},
    }


@router.post("/file-crunch-cleanup")
async def crunch_file_cleanup(req: FileCrunchReq):
    """上传日志文件进行关联分析，分析完成后自动清理临时文件"""
    result = await LogCorrelateService.crunch_file(
        file_path=req.file_path,
        file_paths=req.file_paths if req.file_paths else None,
        file_content=req.file_content,
        time_window_minutes=req.time_window_minutes,
        use_llm=req.use_llm,
    )
    # 清理 upload_temp 中本次上传的临时文件
    if req.file_paths:
        for fp in req.file_paths:
            try:
                if fp.startswith(settings.upload_temp_dir) and os.path.exists(fp):
                    os.remove(fp)
            except OSError as e:
                logger.warning(f"清理临时文件失败 {fp}: {e}")
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
