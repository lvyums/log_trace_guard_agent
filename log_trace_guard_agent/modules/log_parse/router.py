"""日志解析模块 — API 路由"""

from fastapi import APIRouter, Depends

from modules.log_parse.service import LogParseService
from core.context_manager import ContextManager
from app.dependencies import get_context, validate_log_line
from app.exceptions import ParamInvalidException, LogParseFailedException
from app.schemas.log_parse import (
    LogIdentifyReq, LogParseReq, RiskAssessReq,
    FieldExplainReq, FieldExplainBatchReq, BatchParseReq,
)
from common.logger import LogManager

logger = LogManager.get_logger()

router = APIRouter(prefix="/api/v1/log-parse", tags=["日志解析"])


@router.post("/identify")
async def identify_log_type(req: LogIdentifyReq, ctx: ContextManager = Depends(get_context)):
    """识别日志类型"""
    # 入参校验（额外的业务层校验，超出 Pydantic 约束）
    validation = validate_log_line(req.log_line)
    if not validation["valid"]:
        raise ParamInvalidException(validation["error"])

    result = await LogParseService.identify_log_type(req.log_line, ctx)
    return result


@router.post("/parse")
async def parse_log(req: LogParseReq, ctx: ContextManager = Depends(get_context)):
    """结构化解析日志"""
    validation = validate_log_line(req.log_line)
    if not validation["valid"]:
        raise ParamInvalidException(validation["error"])

    result = await LogParseService.parse_log(req.log_line, ctx)
    return result


@router.post("/assess")
async def assess_risk(req: RiskAssessReq, ctx: ContextManager = Depends(get_context)):
    """异常行为研判"""
    validation = validate_log_line(req.log_line)
    if not validation["valid"]:
        raise ParamInvalidException(validation["error"])

    # 先解析，再研判
    parse_result = await LogParseService.parse_log(req.log_line, ctx)
    if parse_result["code"] != 0:
        return parse_result
    result = await LogParseService.assess_risk(parse_result["data"], ctx)
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