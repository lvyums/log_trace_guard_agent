"""模块二：合规审计基线 — 业务编排

三层架构：规则引擎（JSON 关键词匹配）→ RAG（合规知识库检索）→ LLM（智能解读）
"""

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
        """合规标准智能问答

        三层：规则引擎关键词匹配 → RAG 合规知识库补充 → LLM 智能解读
        """
        strategy = ComplianceStrategyFactory.get_strategy("qa")
        if not strategy:
            return Result.fail("合规标准问答策略未注册")

        params = {
            "question": question,
            "asset_type": asset_type,
            "standard_filter": standard_filter,
        }
        result = strategy.execute(params)

        # ── 第2层：RAG 合规知识库检索补充 ──
        rag_items = []
        try:
            from core.ai_base.rag_factory import RAGFactory
            kb = RAGFactory.get_kb("compliance")
            rag_result = kb.retrieve(question, top_k=3)
            rag_items = rag_result.items
            if rag_items:
                logger.info(f"RAG 合规库检索到 {len(rag_items)} 条补充知识")
        except Exception as e:
            logger.debug(f"RAG 合规库检索跳过: {e}")

        # 将 RAG 检索到的标准条目补充到结果中
        if rag_items:
            existing_ids = set()
            for s in result.get("standards", []):
                for item in s.get("items", []):
                    existing_ids.add(item.get("item_id", ""))

            for item in rag_items:
                doc = item.get("document", "")
                meta = item.get("metadata", {})
                item_id = meta.get("item_id", "")
                if item_id and item_id not in existing_ids:
                    # 从文档文本中提取关键信息
                    result.setdefault("rag_supplements", []).append({
                        "item_id": item_id,
                        "document": doc,
                        "score": item.get("score", 0),
                    })

        # ── 第3层：LLM 智能解读（当规则匹配不足或用户需要深度解读时）──
        if not result.get("standards") or result.get("matched_count", 0) < 2:
            try:
                from core.ai_base.llm_factory import LLMFactory
                llm = await LLMFactory.get_light_llm()

                rag_context = ""
                if rag_items:
                    rag_context = "\n相关知识库内容：\n" + "\n".join(
                        f"- {r.get('document', '')[:200]}" for r in rag_items[:3]
                    )

                messages = [
                    {"role": "system", "content": (
                        "你是网络安全合规专家，精通等保2.0、网安法、数据安全法。"
                        "请根据问题和已有规则匹配结果，给出专业、准确的合规建议。"
                        f"{rag_context}"
                    )},
                    {"role": "user", "content": question},
                ]
                resp = await llm.chat(messages)
                if resp.get("success") and resp.get("content"):
                    result["llm_answer"] = resp["content"]
                    logger.info("LLM 合规解读生成成功")
            except Exception as e:
                logger.debug(f"LLM 合规解读跳过: {e}")

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
        logger.info(f"DEBUG: generate_baseline params={params}")
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
            "has_audit_mechanism": has_audit_mechanism,
            "has_ntp": has_ntp,
            "audit_frequency": audit_frequency,
            "has_alert_system": has_alert_system,
            "has_bastion": has_bastion,
            "additional_info": additional_info,
        }
        result = strategy.execute(params)

        # ── 第3层：LLM 增强整改建议（当存在高风险缺口时）──
        gaps = result.get("gaps", [])
        high_risk_gaps = [g for g in gaps if g.get("risk_level") in ("critical", "high")]
        if high_risk_gaps:
            try:
                from core.ai_base.llm_factory import LLMFactory
                llm = await LLMFactory.get_light_llm()

                gap_summary = "\n".join(
                    f"- [{g['risk_level']}] {g['requirement']}: {g['current_status']}"
                    for g in high_risk_gaps[:5]
                )
                messages = [
                    {"role": "system", "content": (
                        "你是网络安全合规整改专家。根据以下合规缺口，给出优先级排序的整改建议。"
                        "每条建议要具体可执行，包含技术方案和管理措施。"
                    )},
                    {"role": "user", "content": f"合规缺口清单：\n{gap_summary}"},
                ]
                resp = await llm.chat(messages)
                if resp.get("success") and resp.get("content"):
                    result["llm_remediation"] = resp["content"]
                    logger.info("LLM 整改建议生成成功")
            except Exception as e:
                logger.debug(f"LLM 整改建议跳过: {e}")

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