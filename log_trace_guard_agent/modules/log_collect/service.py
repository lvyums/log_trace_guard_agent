"""模块三业务逻辑编排 — 采集方案生成 + 故障诊断 + 架构推荐"""

from typing import Optional

from modules.log_collect.collect_strategy import CollectStrategyFactory
from modules.log_collect.device_match import DeviceMatcher
from modules.log_collect.fault_fix import FaultFixer
from core.context_manager import ContextManager, ModuleContext
from common.logger import LogManager
from common.result_util import Result

logger = LogManager.get_logger()


class LogCollectService:
    """日志采集架构指导 — 业务逻辑编排"""

    @staticmethod
    async def match_device(device_type: str, device_model: str = "", scale: str = "small", context: Optional[ContextManager] = None) -> Result:
        """设备类型匹配 — 自动识别并推荐采集方案"""
        # 获取推荐方案
        recommendation = DeviceMatcher.get_recommendation(device_type, device_model, scale)

        plan = recommendation.get("plan")
        plan_dict = None
        if plan:
            plan_dict = {
                "device_type": plan.device_type,
                "device_model": plan.device_model,
                "protocol": plan.protocol,
                "architecture": plan.architecture,
                "config_template": plan.config_template,
                "steps": plan.steps,
                "notes": plan.notes,
            }

        # 更新上下文
        if context:
            ctx = ModuleContext(
                module_id="log_collect",
                status="success" if plan else "warning",
                input={"device_type": device_type, "device_model": device_model, "scale": scale},
                output={"recommendation": recommendation},
            )
            context.set_module_result("log_collect", ctx)

        return Result.ok({
            "device_info": recommendation["device_info"],
            "plan": plan_dict,
            "match_source": recommendation["match_source"],
        })

    @staticmethod
    async def generate_plan(device_type: str, device_model: str = "", scale: str = "small", include_config: bool = True, context: Optional[ContextManager] = None) -> Result:
        """生成采集方案 — 根据设备类型和规模生成完整方案"""
        plan = CollectStrategyFactory.get_plan(device_type, device_model, scale)

        if plan is None:
            return Result.fail(f"暂不支持设备类型: {device_type}")

        plan_dict = {
            "device_type": plan.device_type,
            "device_model": plan.device_model,
            "protocol": plan.protocol,
            "architecture": plan.architecture,
            "steps": plan.steps,
            "notes": plan.notes,
        }

        if include_config:
            plan_dict["config_template"] = plan.config_template

        # 更新上下文
        if context:
            ctx = ModuleContext(
                module_id="log_collect",
                status="success",
                input={"device_type": device_type, "scale": scale},
                output={"plan": plan_dict},
            )
            context.set_module_result("log_collect", ctx)

        return Result.ok(plan_dict)

    @staticmethod
    async def diagnose_fault(symptom: str, device_type: Optional[str] = None, context: Optional[ContextManager] = None) -> Result:
        """故障诊断 — 根据症状自动定位原因并输出修复方案"""
        diagnosis = FaultFixer.diagnose(symptom)

        if diagnosis is None:
            return Result.ok({
                "fault_type": "未识别",
                "fault_desc": f"未匹配到已知故障类型，症状描述: {symptom}",
                "possible_causes": ["请提供更多故障细节以便精准诊断"],
                "fix_steps": ["建议联系技术支持获取帮助"],
                "prevention": [],
                "severity": "unknown",
            })

        result = {
            "fault_type": diagnosis.fault_type,
            "fault_desc": diagnosis.fault_desc,
            "possible_causes": diagnosis.possible_causes,
            "fix_steps": diagnosis.fix_steps,
            "prevention": diagnosis.prevention,
            "severity": diagnosis.severity,
        }

        # 更新上下文
        if context:
            ctx = ModuleContext(
                module_id="log_collect",
                status="success",
                input={"symptom": symptom, "device_type": device_type},
                output={"diagnosis": result},
            )
            context.set_module_result("log_collect", ctx)

        return Result.ok(result)

    @staticmethod
    async def get_fault_list(context: Optional[ContextManager] = None) -> Result:
        """获取所有故障类型列表"""
        faults = FaultFixer.get_all_faults()
        return Result.ok({"faults": faults, "total": len(faults)})

    @staticmethod
    async def recommend_architecture(device_count: int, daily_log_volume: str = "small", budget: str = "low", team_skill: str = "basic", context: Optional[ContextManager] = None) -> Result:
        """架构推荐 — 根据企业规模和预算推荐日志采集架构"""
        # 根据设备数量和日志量级推荐架构
        if device_count <= 10 and daily_log_volume == "small":
            arch = {
                "recommended_arch": "轻量级单机汇聚",
                "architecture_desc": "适用于小型园区/中小企业，日志量 < 5GB/天",
                "components": ["Syslog 服务器", "Filebeat 采集器", "单机 Elasticsearch", "Kibana 可视化"],
                "data_flow": ["设备 → Syslog/Filebeat → ES → Kibana"],
                "estimated_cost": "低（开源方案，服务器成本 < 2万）",
                "pros": ["部署简单", "维护成本低", "快速上线"],
                "cons": ["扩展性有限", "单点故障风险", "查询性能受限"],
            }
        elif device_count <= 100 and daily_log_volume in ("small", "medium"):
            arch = {
                "recommended_arch": "ELK 分布式集群",
                "architecture_desc": "适用于中型企业，日志量 5-50GB/天",
                "components": ["Kafka 缓冲层", "Logstash 解析", "ES 集群(3节点)", "Kibana 可视化", "Filebeat 采集器"],
                "data_flow": ["设备 → Filebeat → Kafka → Logstash → ES → Kibana"],
                "estimated_cost": "中等（服务器成本 5-15万）",
                "pros": ["高可用", "可扩展", "性能优秀"],
                "cons": ["运维复杂度较高", "需要专业团队"],
            }
        else:
            arch = {
                "recommended_arch": "企业级 SIEM 架构",
                "architecture_desc": "适用于大型政企/园区，日志量 > 50GB/天",
                "components": ["Kafka 集群", "Flink 实时计算", "ES 集群(6+节点)", "SIEM 平台", "SOAR 编排", "告警中心"],
                "data_flow": ["设备 → 采集代理 → Kafka → Flink → ES/SIEM → 告警/SOAR"],
                "estimated_cost": "高（服务器成本 30万+，含商业 SIEM 授权）",
                "pros": ["高性能", "高可用", "智能化", "合规审计"],
                "cons": ["成本高", "需要专业安全团队", "建设周期长"],
            }

        # 更新上下文
        if context:
            ctx = ModuleContext(
                module_id="log_collect",
                status="success",
                input={"device_count": device_count, "daily_log_volume": daily_log_volume},
                output={"architecture": arch},
            )
            context.set_module_result("log_collect", ctx)

        return Result.ok(arch)
