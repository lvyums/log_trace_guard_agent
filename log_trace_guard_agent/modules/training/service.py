"""模块五：交互式攻防实训模块 — 业务编排"""

from typing import Optional

from modules.training.task_engine import TaskEngine
from modules.training.check_strategy import CheckStrategyFactory
from modules.training.error_analysis import ErrorAnalysis
from modules.training.report_gen import ReportGenerator
from core.context_manager import ContextManager, ModuleContext
from app.schemas.context_schema import ModuleStatus
from common.logger import LogManager
from common.result_util import Result

logger = LogManager.get_logger()


class TrainingService:
    """交互式攻防实训 — 业务编排"""

    # ── 任务下发 ──

    @staticmethod
    async def dispatch_tasks(scenario_id: Optional[str] = None,
                              category: Optional[str] = None,
                              context: Optional[ContextManager] = None) -> Result:
        """下发实训任务"""
        result = TaskEngine.dispatch(scenario_id=scenario_id, category=category)

        if not result:
            return Result.ok({
                "scenarios": [],
                "total": 0,
                "message": "未找到匹配的实训场景",
            })

        if context:
            ctx = ModuleContext(
                module_id="training",
                status=ModuleStatus.SUCCESS,
                input={"scenario_id": scenario_id, "category": category},
                output={"total_scenarios": len(result)},
            )
            context.set_module_result("training", ctx)

        return Result.ok({
            "scenarios": result,
            "total": len(result),
        })

    # ── 答案提交与校验 ──

    @staticmethod
    async def submit_answer(scenario_id: str, task_id: str,
                             submit_type: str, content: dict,
                             student_id: Optional[str] = None,
                             context: Optional[ContextManager] = None) -> Result:
        """提交答案并执行双维度校验"""
        # 1. 获取标准答案
        standard = TaskEngine.get_standard_answer(scenario_id, task_id)
        if not standard:
            return Result.fail(f"未找到场景 {scenario_id} 任务 {task_id} 的标准答案")

        # 2. 获取校验策略
        strategy = CheckStrategyFactory.get_strategy(submit_type)
        if not strategy:
            return Result.fail(f"未知的提交类型: {submit_type}，支持的类型: rule/script/conclusion/plan")

        # 3. 执行双维度校验
        check_result = await strategy.check(content, standard)

        # 4. 生成原理讲解
        task = TaskEngine.get_task(scenario_id, task_id)
        task_title = task.get("title", "")

        analysis_text = ErrorAnalysis.analyze(
            task_type=task.get("submit_type", ""),
            submit_type=submit_type,
            task_title=task_title,
            checks=check_result.get("checks", []),
            score=check_result.get("score", 0),
            grade=check_result.get("grade", "C"),
        )

        # 5. 记录学员成绩
        if not student_id:
            student_id = f"anonymous_{scenario_id}_{task_id}"

        TaskEngine.record_submission(
            student_id=student_id,
            scenario_id=scenario_id,
            task_id=task_id,
            score=check_result["score"],
            grade=check_result["grade"],
            status=check_result["status"],
        )

        # 6. 组装响应
        response = {
            "task_id": task_id,
            "scenario_id": scenario_id,
            "score": check_result["score"],
            "grade": check_result["grade"],
            "status": check_result["status"],
            "checks": check_result["checks"],
            "analysis": analysis_text,
            "suggestion": check_result.get("suggestion"),
            "correct_answer": check_result.get("correct_answer"),
        }

        if context:
            ctx = ModuleContext(
                module_id="training",
                status=ModuleStatus.SUCCESS if check_result["status"] == "passed" else ModuleStatus.PARTIAL,
                input={"scenario_id": scenario_id, "task_id": task_id, "submit_type": submit_type},
                output={"score": check_result["score"], "grade": check_result["grade"]},
            )
            context.set_module_result("training", ctx)

        return Result.ok(response)

    # ── 实训报告 ──

    @staticmethod
    async def generate_report(student_id: Optional[str] = None,
                               scenario_id: Optional[str] = None,
                               context: Optional[ContextManager] = None) -> Result:
        """生成实训报告"""
        if not student_id:
            student_id = "anonymous"

        report = ReportGenerator.generate_report(
            student_id=student_id,
            scenario_id=scenario_id,
        )

        if context:
            ctx = ModuleContext(
                module_id="training",
                status=ModuleStatus.SUCCESS,
                input={"student_id": student_id, "scenario_id": scenario_id},
                output={"total_tasks": report["total_tasks"], "average_score": report["average_score"]},
            )
            context.set_module_result("training", ctx)

        return Result.ok(report)