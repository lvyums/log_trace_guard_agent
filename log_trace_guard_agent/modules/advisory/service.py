"""规划咨询模块 — 业务编排"""

from typing import Optional

from modules.advisory.arch_strategy import arch_recommend_strategy
from modules.advisory.platform_strategy import platform_choose_strategy
from core.context_manager import ContextManager, ModuleContext
from core.ai_base.prompt_manager import PromptManager
from core.ai_base.rag_factory import RAGFactory
from core.ai_base.llm_factory import LLMFactory
from app.schemas.context_schema import ModuleStatus
from app.exceptions import ParamInvalidException, LLMTimeoutException
from common.logger import LogManager
from common.result_util import Result

logger = LogManager.get_logger()

SCALE_MAP = {"small": "小型（<100人）", "medium": "中型（100-1000人）", "large": "大型（>1000人）"}


class AdvisoryService:
    """规划咨询 — 业务逻辑编排"""

    @staticmethod
    async def recommend_architecture(
        device_count: int,
        daily_log_volume: str = "small",
        budget: str = "low",
        team_skill: str = "basic",
        context: Optional[ContextManager] = None,
    ) -> Result:
        """架构推荐"""
        if device_count < 1:
            raise ParamInvalidException("设备数量必须大于0")
        if daily_log_volume not in ("small", "medium", "large"):
            raise ParamInvalidException(f"无效的日志量级: {daily_log_volume}")

        arch = arch_recommend_strategy.recommend(device_count, daily_log_volume)

        # 更新上下文
        if context:
            ctx = ModuleContext(
                module_id="advisory",
                status=ModuleStatus.SUCCESS,
                input={"device_count": device_count, "daily_log_volume": daily_log_volume},
                output={"architecture": arch},
            )
            context.set_module_result("advisory", ctx)

        return Result.ok(arch)

    @staticmethod
    async def recommend_platform(
        device_count: int,
        daily_log_volume: str = "medium",
        budget: str = "medium",
        team_skill: str = "basic",
        requirements: Optional[list[str]] = None,
        context: Optional[ContextManager] = None,
    ) -> Result:
        """平台选型推荐"""
        if device_count < 1:
            raise ParamInvalidException("设备数量必须大于0")

        result = platform_choose_strategy.recommend(
            device_count=device_count,
            daily_log_volume=daily_log_volume,
            budget=budget,
            team_skill=team_skill,
            requirements=requirements,
        )

        # 更新上下文
        if context:
            ctx = ModuleContext(
                module_id="advisory",
                status=ModuleStatus.SUCCESS,
                input={
                    "device_count": device_count,
                    "daily_log_volume": daily_log_volume,
                    "budget": budget,
                    "team_skill": team_skill,
                },
                output=result,
            )
            context.set_module_result("advisory", ctx)

        return Result.ok(result)

    @staticmethod
    async def generate_guide(
        scale: str,
        device_types: list[str],
        device_count: int,
        daily_log_volume: str = "medium",
        budget: str = "medium",
        team_skill: str = "basic",
        collect_plans: Optional[list[dict]] = None,
        architecture: Optional[dict] = None,
        platform: Optional[dict] = None,
        context: Optional[ContextManager] = None,
    ) -> Result:
        """生成指导手册"""
        if scale not in ("small", "medium", "large"):
            raise ParamInvalidException(f"无效的企业规模: {scale}")
        if not device_types:
            raise ParamInvalidException("请至少选择一种设备类型")

        import json

        # 组装 Prompt
        scale_label = SCALE_MAP.get(scale, scale)
        device_types_str = "、".join(device_types)

        user_prompt = PromptManager.get_prompt(
            "guide_generate",
            scale=scale_label,
            device_types=device_types_str,
            device_count=device_count,
            daily_log_volume=daily_log_volume,
            budget=budget,
            team_skill=team_skill,
            collect_plans_json=json.dumps(collect_plans or [], ensure_ascii=False, indent=2),
            architecture_json=json.dumps(architecture or {}, ensure_ascii=False, indent=2),
            platform_json=json.dumps(platform or {}, ensure_ascii=False, indent=2),
        )

        # 调用 LLM
        llm = await LLMFactory.get_main_llm()
        messages = [
            {"role": "system", "content": PromptManager.get_system_prompt("default")},
            {"role": "user", "content": user_prompt},
        ]

        response = await llm.chat(messages, temperature=0.3, timeout=120)

        if not response.get("success"):
            error_msg = response.get("error", "未知错误")
            if "402" in str(error_msg) or "quota" in str(error_msg).lower() or "欠费" in str(error_msg):
                raise LLMTimeoutException("AI 服务配额不足，请联系管理员充值后重试")
            raise LLMTimeoutException(f"AI 生成失败: {error_msg}")

        content = response.get("content", "")

        # 更新上下文
        if context:
            ctx = ModuleContext(
                module_id="advisory",
                status=ModuleStatus.SUCCESS,
                input={"scale": scale, "device_types": device_types, "device_count": device_count},
                output={"content_length": len(content)},
            )
            context.set_module_result("advisory_guide", ctx)

        return Result.ok({"content": content})
