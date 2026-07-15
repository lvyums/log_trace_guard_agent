"""模块二：合规审计基线 — 业务编排"""

from typing import Optional

from modules.compliance.compliance_rule import ComplianceStrategyFactory
from core.context_manager import ContextManager, ModuleContext
from app.schemas.context_schema import ModuleStatus
from common.logger import LogManager
from common.result_util import Result

logger = LogManager.get_logger()


class ComplianceService:
    """合规审计基线 — 业务编排"""

    # ── 合规标准智能问答 ──

    @staticmethod
    async def compliance_qa(question: str, asset_type: Optional[str] = None,
                            standard_filter: Optional[str] = None,
                            context: Optional[ContextManager] = None) -> Result:
        """合规标准智能问答"""
        strategy = ComplianceStrategyFactory.get_strategy("qa")
        if not strategy:
            return Result.fail("合规标准问答策略未注册")

        params = {
            "question": question,
            "asset_type": asset_type,
            "standard_filter": standard_filter,
        }
        result = strategy.execute(params)

        if context:
            ctx = ModuleContext(
                module_id="compliance",
                status=ModuleStatus.SUCCESS if result.get("matched_count", 0) > 0 else ModuleStatus.WARNING,
                input=params,
                output=result,
            )
            context.set_module_result("compliance", ctx)

        return Result.ok(result)

    # ── 合规基线自动生成 ──

    @staticmethod
    async def generate_baseline(asset_count: int, business_type: str = "enterprise",
                                device_types: Optional[list[str]] = None,
                                monitor_scenarios: Optional[list[str]] = None,
                                industry: Optional[str] = None,
                                context: Optional[ContextManager] = None) -> Result:
        """个性化合规基线自动生成"""
        strategy = ComplianceStrategyFactory.get_strategy("baseline_gen")
        if not strategy:
            return Result.fail("合规基线生成策略未注册")

        params = {
            "asset_count": asset_count,
            "business_type": business_type,
            "device_types": device_types or [],
            "monitor_scenarios": monitor_scenarios,
            "industry": industry,
        }
        result = strategy.execute(params)

        if context:
            ctx = ModuleContext(
                module_id="compliance",
                status=ModuleStatus.SUCCESS if result.get("baselines") else ModuleStatus.WARNING,
                input=params,
                output=result,
            )
            context.set_module_result("compliance", ctx)

        return Result.ok(result)

    # ── 合规自查与缺口整改 ──

    @staticmethod
    async def compliance_check(log_retention_days: Optional[int] = None,
                                has_backup: Optional[bool] = None,
                                has_tamper_proof: Optional[bool] = None,
                                backup_frequency: Optional[str] = None,
                                device_count: Optional[int] = None,
                                has_audit_mechanism: Optional[bool] = None,
                                has_ntp: Optional[bool] = None,
                                audit_frequency: Optional[str] = None,
                                has_alert_system: Optional[bool] = None,
                                has_bastion: Optional[bool] = None,
                                additional_info: Optional[str] = None,
                                context: Optional[ContextManager] = None) -> Result:
        """合规自查与缺口整改"""
        strategy = ComplianceStrategyFactory.get_strategy("check")
        if not strategy:
            return Result.fail("合规自查策略未注册")

        params = {
            "log_retention_days": log_retention_days,
            "has_backup": has_backup,
            "has_tamper_proof": has_tamper_proof,
            "backup_frequency": backup_frequency,
            "device_count": device_count,
            "has_audit": has_audit_mechanism,
            "has_ntp": has_ntp,
            "audit_frequency": audit_frequency,
            "has_alert": has_alert_system,
            "has_bastion": has_bastion,
            "additional_info": additional_info,
        }
        result = strategy.execute(params)

        if context:
            ctx = ModuleContext(
                module_id="compliance",
                status=ModuleStatus.SUCCESS,
                input=params,
                output=result,
            )
            context.set_module_result("compliance", ctx)

        return Result.ok(result)

    # ── 批量合规自查 ──

    @staticmethod
    async def compliance_check_batch(checks: list[dict], context: Optional[ContextManager] = None) -> Result:
        """批量合规自查"""
        items = []
        for i, check in enumerate(checks):
            result = await ComplianceService.compliance_check(
                log_retention_days=check.get("log_retention_days"),
                has_backup=check.get("has_backup"),
                has_tamper_proof=check.get("has_tamper_proof"),
                backup_frequency=check.get("backup_frequency"),
                device_count=check.get("device_count"),
                has_audit_mechanism=check.get("has_audit_mechanism"),
                has_ntp=check.get("has_ntp"),
                audit_frequency=check.get("audit_frequency"),
                has_alert_system=check.get("has_alert_system"),
                has_bastion=check.get("has_bastion"),
                additional_info=check.get("additional_info"),
                context=context,
            )
            items.append({
                "index": i,
                "result": result.get("data") if result["code"] == 0 else None,
                "error": None if result["code"] == 0 else result["msg"],
            })

        return Result.ok({
            "total": len(checks),
            "success_count": sum(1 for i in items if i["result"]),
            "fail_count": sum(1 for i in items if i["error"]),
            "items": items,
        })