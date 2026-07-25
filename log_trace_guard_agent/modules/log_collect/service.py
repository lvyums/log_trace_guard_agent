"""模块三业务逻辑编排 — 参数校验 + RAG增强 + 批量支持 + 配置化阈值"""

from typing import Optional

from modules.log_collect.collect_strategy import CollectStrategyFactory
from modules.log_collect.device_match import DeviceMatcher
from modules.log_collect.fault_fix import FaultFixer
from core.context_manager import ContextManager, ModuleContext
from app.exceptions import ParamInvalidException
from app.schemas.context_schema import ModuleStatus
from app.settings import settings
from common.json_util import JsonConfigLoader
from common.logger import LogManager
from common.result_util import Result

logger = LogManager.get_logger()


class LogCollectService:
    """日志采集架构指导 — 业务逻辑编排"""

    @staticmethod
    async def match_device(device_type: str, device_model: str = "", scale: str = "small", context: Optional[ContextManager] = None) -> Result:
        """设备类型匹配 — 自动识别并推荐采集方案"""
        # 参数校验
        if not device_type or not device_type.strip():
            raise ParamInvalidException("设备类型不能为空")
        device_type = device_type.strip().lower()
        if scale not in ("small", "medium", "large"):
            raise ParamInvalidException(f"无效的规模参数: {scale}，可选: small/medium/large")

        # 获取推荐方案
        recommendation = DeviceMatcher.get_recommendation(device_type, device_model, scale)

        plan = recommendation.get("plan")
        plan_dict = _plan_to_dict(plan) if plan else None
        confidence = recommendation.get("match_confidence", 0)

        # 低置信度附加人工确认提示
        low_confidence_note = None
        if confidence < settings.match_confidence_threshold:
            low_confidence_note = f"匹配置信度较低({confidence:.1f}分)，建议人工确认设备类型"

        # RAG 增强：从采集知识库补充小众设备适配说明
        rag_supplements = []
        if plan and plan.rag_supplements:
            rag_supplements = plan.rag_supplements

        # 更新上下文
        if context:
            ctx = ModuleContext(
                module_id="log_collect",
                status=ModuleStatus.SUCCESS if plan else ModuleStatus.WARNING,
                input={"device_type": device_type, "device_model": device_model, "scale": scale},
                output={"recommendation": recommendation},
            )
            context.set_module_result("log_collect", ctx)

        result_data = {
            "device_info": recommendation["device_info"],
            "plan": plan_dict,
            "match_source": recommendation["match_source"],
            "match_confidence": confidence,
        }
        if low_confidence_note:
            result_data["low_confidence_note"] = low_confidence_note
        if rag_supplements:
            result_data["rag_supplements"] = rag_supplements

        return Result.ok(result_data)

    @staticmethod
    async def generate_plan(device_type: str, device_model: str = "", scale: str = "small", include_config: bool = True, context: Optional[ContextManager] = None) -> Result:
        """生成采集方案 — 含 RAG 增强"""
        # 参数校验
        if not device_type or not device_type.strip():
            raise ParamInvalidException("设备类型不能为空")
        device_type = device_type.strip().lower()
        if scale not in ("small", "medium", "large"):
            raise ParamInvalidException(f"无效的规模参数: {scale}")

        plan = CollectStrategyFactory.get_plan(device_type, device_model, scale)

        # RAG 增强：从采集知识库补充特殊环境适配说明
        rag_supplements = _get_rag_supplements(device_type, device_model)

        plan_dict = _plan_to_dict(plan, include_config)
        if rag_supplements:
            plan_dict["rag_supplements"] = rag_supplements

        # 更新上下文
        if context:
            ctx = ModuleContext(
                module_id="log_collect",
                status=ModuleStatus.SUCCESS,
                input={"device_type": device_type, "scale": scale},
                output={"plan": plan_dict},
            )
            context.set_module_result("log_collect", ctx)

        return Result.ok(plan_dict)

    @staticmethod
    async def batch_generate_plans(devices: list[dict], context: Optional[ContextManager] = None) -> Result:
        """批量生成采集方案 — 支持多设备汇总"""
        if not devices:
            raise ParamInvalidException("设备列表不能为空")
        if len(devices) > 50:
            raise ParamInvalidException("单次批量请求最多50台设备")

        items = []
        protocol_summary = {}
        for i, device in enumerate(devices):
            device_type = device.get("device_type", "").strip().lower()
            device_model = device.get("device_model", "")
            scale = device.get("scale", "small")

            if not device_type:
                items.append({"index": i, "device_type": "", "error": "设备类型不能为空"})
                continue

            plan = CollectStrategyFactory.get_plan(device_type, device_model, scale)
            plan_dict = _plan_to_dict(plan) if plan else None

            # 汇总协议分布
            protocol = plan.protocol if plan else "unknown"
            protocol_summary[protocol] = protocol_summary.get(protocol, 0) + 1

            items.append({
                "index": i,
                "device_type": device_type,
                "device_model": device_model,
                "plan": plan_dict,
            })

        # 更新上下文
        if context:
            ctx = ModuleContext(
                module_id="log_collect",
                status=ModuleStatus.SUCCESS,
                input={"batch_size": len(devices)},
                output={"items": items, "protocol_summary": protocol_summary},
            )
            context.set_module_result("log_collect", ctx)

        return Result.ok({
            "total": len(devices),
            "success_count": sum(1 for i in items if i.get("plan")),
            "fail_count": sum(1 for i in items if i.get("error")),
            "items": items,
            "protocol_summary": protocol_summary,
        })

    @staticmethod
    async def diagnose_fault(
        symptom: str,
        device_type: Optional[str] = None,
        protocol: Optional[str] = None,
        error_log: Optional[str] = None,
        context: Optional[ContextManager] = None,
    ) -> Result:
        """故障诊断 — 多维度联合诊断"""
        # 参数校验
        if not symptom or not symptom.strip():
            raise ParamInvalidException("故障症状描述不能为空")

        best_diagnosis, candidates = FaultFixer.diagnose(
            symptom=symptom,
            protocol=protocol,
            device_type=device_type,
            error_log=error_log,
        )

        # 关键词匹配不足时，降级调用大模型智能诊断
        use_llm = best_diagnosis is None or best_diagnosis.match_score < 30
        if use_llm:
            logger.info(f"关键词匹配不足 ({best_diagnosis.match_score if best_diagnosis else 0}), 降级到 LLM 诊断")
            llm_diagnosis = await FaultFixer.diagnose_with_llm(
                symptom=symptom,
                protocol=protocol,
                device_type=device_type,
                error_log=error_log,
            )
            if llm_diagnosis:
                best_diagnosis = llm_diagnosis

        if best_diagnosis is None:
            # 无精确匹配 — 显示 Top-N 候选，降低挫败感
            top_candidates = []
            for c in candidates[:3]:
                top_candidates.append({
                    "fault_type": c.diagnosis.fault_type,
                    "match_score": c.diagnosis.match_score,
                    "matched_keywords": c.matched_keywords[:5],
                })
            result = {
                "fault_type": "未识别",
                "fault_desc": f"未精确匹配到已知故障类型，症状描述: {symptom}",
                "match_score": 0,
                "possible_causes": ["请提供更多故障细节以便精准诊断"],
                "fix_steps": ["建议参考以下相近故障排查方案"],
                "prevention": [],
                "severity": "unknown",
                "candidates": top_candidates,
            }
        else:
            result = {
                "fault_type": best_diagnosis.fault_type,
                "fault_desc": best_diagnosis.fault_desc,
                "match_score": best_diagnosis.match_score,
                "possible_causes": best_diagnosis.possible_causes,
                "fix_steps": best_diagnosis.fix_steps,
                "prevention": best_diagnosis.prevention,
                "severity": best_diagnosis.severity,
                "candidates": [
                    {
                        "fault_type": c.diagnosis.fault_type,
                        "match_score": c.diagnosis.match_score,
                        "matched_keywords": c.matched_keywords[:5],
                    }
                    for c in candidates[1:4]
                    if c.score > 0
                ],
            }

        # 更新上下文
        if context:
            ctx = ModuleContext(
                module_id="log_collect",
                status=ModuleStatus.SUCCESS,
                input={"symptom": symptom, "device_type": device_type, "protocol": protocol},
                output={"diagnosis": result},
            )
            context.set_module_result("log_collect", ctx)

        return Result.ok(result)

    @staticmethod
    async def get_fault_list(context: Optional[ContextManager] = None) -> Result:
        """获取所有故障类型列表"""
        faults = FaultFixer.get_all_faults()
        return Result.ok({"faults": faults, "total": len(faults)})



# ── 私有辅助函数 ──

def _plan_to_dict(plan, include_config: bool = True) -> dict:
    """CollectPlan 转字典"""
    d = {
        "device_type": plan.device_type,
        "device_model": plan.device_model,
        "protocol": plan.protocol,
        "architecture": plan.architecture,
        "steps": plan.steps,
        "notes": plan.notes,
    }
    if include_config:
        d["config_template"] = plan.config_template
    if plan.rag_supplements:
        d["rag_supplements"] = plan.rag_supplements
    return d


def _get_rag_supplements(device_type: str, device_model: str) -> list[str]:
    """从采集知识库获取 RAG 补充说明"""
    try:
        # 延迟导入：避免 openai 等依赖缺失导致模块加载失败
        from core.ai_base.rag_factory import RAGFactory
        query = f"{device_type} {device_model} 采集方案 特殊环境".strip()
        kb = RAGFactory.get_kb("collection")
        result = kb.retrieve(query, top_k=2)
        if result.items:
            return [item.get("document", "")[:200] for item in result.items if item.get("document")]
    except Exception as e:
        logger.debug(f"RAG 采集知识库检索跳过: {e}")
    return []