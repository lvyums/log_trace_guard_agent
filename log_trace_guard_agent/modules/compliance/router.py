"""模块二：合规审计基线 — API 路由"""

from fastapi import APIRouter, Depends

from modules.compliance.service import ComplianceService
from modules.compliance.schemas import (
    ComplianceQAReq, ComplianceQAResp,
    BaselineGenReq, BaselineGenResp,
    ComplianceCheckReq, ComplianceCheckResp,
)
from core.context_manager import ContextManager
from app.dependencies import get_context
from common.logger import LogManager

logger = LogManager.get_logger()

router = APIRouter(prefix="/api/v1/compliance", tags=["合规审计基线"])


@router.post("/qa", response_model=dict)
async def compliance_qa(req: ComplianceQAReq, ctx: ContextManager = Depends(get_context)):
    """合规标准智能问答"""
    result = await ComplianceService.compliance_qa(
        question=req.question,
        asset_type=req.asset_type,
        standard_filter=req.standard_filter,
        context=ctx,
    )
    return result


@router.post("/baseline", response_model=dict)
async def generate_baseline(req: BaselineGenReq, ctx: ContextManager = Depends(get_context)):
    """个性化合规基线自动生成"""
    result = await ComplianceService.generate_baseline(
        asset_count=req.asset_count,
        business_type=req.business_type,
        device_types=req.device_types,
        monitor_scenarios=req.monitor_scenarios,
        industry=req.industry,
        context=ctx,
    )
    return result


@router.post("/check", response_model=dict)
async def compliance_check(req: ComplianceCheckReq, ctx: ContextManager = Depends(get_context)):
    """合规自查与缺口整改"""
    result = await ComplianceService.compliance_check(
        log_retention_days=req.log_retention_days,
        has_backup=req.has_backup,
        has_tamper_proof=req.has_tamper_proof,
        backup_frequency=req.backup_frequency,
        device_count=req.device_count,
        has_audit_mechanism=req.has_audit_mechanism,
        has_ntp=req.has_ntp,
        audit_frequency=req.audit_frequency,
        has_alert_system=req.has_alert_system,
        has_bastion=req.has_bastion,
        additional_info=req.additional_info,
        context=ctx,
    )
    return result


@router.post("/check/batch", response_model=dict)
async def compliance_check_batch(req: list[ComplianceCheckReq], ctx: ContextManager = Depends(get_context)):
    """批量合规自查"""
    checks = [c.model_dump() for c in req]
    result = await ComplianceService.compliance_check_batch(checks, context=ctx)
    return result