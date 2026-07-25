"""日志解析模块 — API 路由"""

import os
import uuid
from typing import List

from fastapi import APIRouter, Depends, UploadFile, File

from modules.log_parse.service import LogParseService
from core.context_manager import ContextManager
from app.dependencies import get_context
from app.schemas.log_parse import (
    LogIdentifyReq, LogParseReq, RiskAssessReq,
    FieldExplainReq, FieldExplainBatchReq, BatchParseReq, BatchFileParseReq,
)
from app.settings import settings
from common.file_util import parse_upload_file
from common.logger import LogManager

logger = LogManager.get_logger()

router = APIRouter(prefix="/api/v1/log-parse", tags=["日志解析"])


@router.post("/identify")
async def identify_log_type(req: LogIdentifyReq, ctx: ContextManager = Depends(get_context)):
    """识别日志类型"""
    result = await LogParseService.identify_log_type(req.log_line, ctx)
    return result


@router.post("/parse")
async def parse_log(req: LogParseReq, ctx: ContextManager = Depends(get_context)):
    """结构化解析日志"""
    result = await LogParseService.parse_log(req.log_line, ctx)
    return result


@router.post("/assess")
async def assess_risk(req: RiskAssessReq, ctx: ContextManager = Depends(get_context)):
    """异常行为研判"""
    # 先解析，再研判（传入可选的 device_type）
    parse_result = await LogParseService.parse_log(req.log_line, ctx)
    if parse_result["code"] != 0:
        return parse_result
    result = await LogParseService.assess_risk(
        parse_result["data"], ctx, device_type=req.device_type
    )
    return result


@router.post("/explain")
async def explain_field(req: FieldExplainReq, ctx: ContextManager = Depends(get_context)):
    """字段释义问答"""
    result = await LogParseService.explain_field(req.field_name, req.device_type, ctx)
    return result


@router.post("/explain/batch")
async def explain_fields_batch(req: FieldExplainBatchReq, ctx: ContextManager = Depends(get_context)):
    """批量字段释义"""
    result = await LogParseService.explain_fields_batch(req.field_names, req.device_type, ctx)
    return result


@router.post("/parse/batch")
async def batch_parse(req: BatchParseReq, ctx: ContextManager = Depends(get_context)):
    """批量解析日志"""
    result = await LogParseService.batch_parse(req.logs, do_assess=req.assess, context=ctx)
    return result


@router.post("/upload")
async def upload_files(files: List[UploadFile] = File(..., description="日志文件（支持多文件）")):
    """上传日志文件，返回保存路径供 batch-file 使用"""
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


@router.post("/parse/batch-file")
async def batch_file_parse(req: BatchFileParseReq, ctx: ContextManager = Depends(get_context)):
    """从上传的文件批量解析日志"""
    all_lines: list[str] = []
    missing_files: list[str] = []

    for fp in req.file_paths:
        lines = parse_upload_file(fp)
        if not lines and not os.path.exists(fp):
            missing_files.append(fp)
        all_lines.extend(lines)

    if missing_files:
        logger.warning(f"以下文件不存在或已删除: {missing_files}")

    if not all_lines:
        return {"code": 1, "msg": "未从文件中解析到有效日志行（文件可能已删除）", "data": None}

    # 限制最大条数，避免超时
    if len(all_lines) > 500:
        all_lines = all_lines[:500]
        logger.warning(f"文件日志行数超过500，已截断")

    result = await LogParseService.batch_parse(all_lines, do_assess=req.assess, context=ctx)
    return result


@router.post("/cleanup")
async def cleanup_files(req: BatchFileParseReq):
    """清理上传的临时文件"""
    cleaned = 0
    for fp in req.file_paths:
        try:
            if fp.startswith(settings.upload_temp_dir) and os.path.exists(fp):
                os.remove(fp)
                cleaned += 1
        except OSError as e:
            logger.warning(f"清理临时文件失败 {fp}: {e}")
    return {"code": 0, "msg": f"已清理 {cleaned} 个文件", "data": {"cleaned": cleaned}}