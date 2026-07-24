"""模块五：实训测评与报告生成 — 全程记录、自动分析薄弱项、生成标准化报告"""

from typing import Optional
import json

from modules.training.task_engine import TaskEngine
from common.logger import LogManager

logger = LogManager.get_logger()


class ReportGenerator:
    """实训报告生成器 — 分析学员操作轨迹，生成标准化报告"""

    # 薄弱项分析模板
    WEAKNESS_CATEGORIES = {
        "regex": {
            "label": "正则表达式能力",
            "keywords": ["正则", "提取", "regex", "pattern"],
            "suggestion": "建议系统学习正则表达式基础（字符类、量词、分组、捕获组），结合在线工具（regex101.com）多加练习",
        },
        "sql_injection": {
            "label": "SQL注入分析能力",
            "keywords": ["sql", "注入", "union", "or"],
            "suggestion": "建议深入学习SQL注入原理（联合查询、报错注入、盲注、堆叠注入），掌握WAF规则配置",
        },
        "trace_chain": {
            "label": "溯源链路分析能力",
            "keywords": ["溯源", "链路", "lateral", "横向", "攻击链"],
            "suggestion": "建议学习ATT&CK框架各阶段攻击手法，掌握多源日志关联分析方法",
        },
        "compliance": {
            "label": "合规审计能力",
            "keywords": ["合规", "等保", "整改", "gap", "gap"],
            "suggestion": "建议系统学习等保2.0三级标准，了解日志管理、访问控制、安全审计等核心要求",
        },
        "es_query": {
            "label": "ES检索语句编写能力",
            "keywords": ["es", "query", "检索", "elastic", "dsl"],
            "suggestion": "建议学习ES Query DSL语法（bool查询、term/match/range、聚合分析），多参考官方文档",
        },
        "plan_design": {
            "label": "方案设计能力",
            "keywords": ["方案", "plan", "架构", "整改", "步骤"],
            "suggestion": "建议学习结构化方案设计方法（问题分析→方案设计→实施计划→效果评估），注意方案的完整性和可落地性",
        },
    }

    @classmethod
    def generate_report(cls, student_id: str,
                        scenario_id: Optional[str] = None) -> dict:
        """生成实训报告"""
        records = TaskEngine.get_student_records(student_id, scenario_id)

        if not records:
            return {
                "student_id": student_id,
                "scenario_name": None,
                "total_tasks": 0,
                "completed_tasks": 0,
                "average_score": 0.0,
                "overall_grade": "N/A",
                "task_records": [],
                "weaknesses": [],
                "improvement_plan": "暂无实训记录，请先完成实训任务。",
                "summary": "尚未开始实训。",
            }

        # 收集任务记录
        task_records = []
        # 根据 scenario_id 是否传入，records 结构不同：
        # 有 scenario_id: {task_id: [records]}
        # 无 scenario_id: {scenario_id: {task_id: [records]}}
        if scenario_id:
            scenarios_data = {scenario_id: records}
        else:
            scenarios_data = records

        for sid, tasks_inner in scenarios_data.items():
            scenario = TaskEngine.get_scenario(sid)
            scenario_name = scenario.get("name", sid) if scenario else sid

            for tid, submissions in tasks_inner.items():
                best = max(submissions, key=lambda r: r["score"])
                task = TaskEngine.get_task(sid, tid)
                task_title = task.get("title", tid) if task else tid

                # 获取标准答案（参考答案+指导）
                standard = TaskEngine.get_standard_answer(sid, tid)
                reference_answer = None
                if standard:
                    ca = standard.get("correct_answer", {})
                    kf = standard.get("key_fields", {})
                    sr = standard.get("scoring_rules", {})
                    # 从 scenario 获取 hint
                    hint = task.get("hint", "") if task else ""

                    # 构建简洁的参考答案展示
                    answer_parts = []
                    for field_name, value in ca.items():
                        if field_name == "reasoning":
                            continue
                        if isinstance(value, list):
                            answer_parts.append(f"• {field_name}: {', '.join(str(v) for v in value)}")
                        elif isinstance(value, dict):
                            answer_parts.append(f"• {field_name}: {json.dumps(value, ensure_ascii=False, indent=2)}")
                        else:
                            answer_parts.append(f"• {field_name}: {value}")

                    reference_answer = {
                        "correct_answer": ca,
                        "key_fields": kf,
                        "scoring_rules": sr,
                        "reasoning": ca.get("reasoning", ""),
                        "hint": hint,
                        "required_fields": sr.get("required_fields", []),
                        "answer_summary": "\n".join(answer_parts),
                    }

                task_records.append({
                    "task_id": tid,
                    "title": task_title,
                    "score": best["score"],
                    "grade": best["grade"],
                    "attempts": len(submissions),
                    "status": best["status"],
                    "reference_answer": reference_answer,
                })

        if not task_records:
            return {
                "student_id": student_id,
                "scenario_name": None,
                "total_tasks": 0,
                "completed_tasks": 0,
                "average_score": 0.0,
                "overall_grade": "N/A",
                "task_records": [],
                "weaknesses": [],
                "improvement_plan": "暂无实训记录。",
                "summary": "尚未开始实训。",
            }

        # 计算统计
        total_tasks = len(task_records)
        completed_tasks = sum(1 for t in task_records if t["status"] == "passed")
        average_score = sum(t["score"] for t in task_records) / total_tasks
        overall_grade = cls._calc_overall_grade(average_score)

        # 薄弱项分析
        weaknesses = cls._analyze_weaknesses(task_records)

        # 能力提升方案
        improvement_plan = cls._build_improvement_plan(weaknesses, average_score)

        # 实训总结
        summary = cls._build_summary(task_records, average_score, overall_grade, weaknesses)

        scenario_name = None
        if scenario_id:
            scenario = TaskEngine.get_scenario(scenario_id)
            scenario_name = scenario.get("name") if scenario else None

        return {
            "student_id": student_id,
            "scenario_name": scenario_name,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "average_score": round(average_score, 1),
            "overall_grade": overall_grade,
            "task_records": task_records,
            "weaknesses": weaknesses,
            "improvement_plan": improvement_plan,
            "summary": summary,
        }

    @classmethod
    def _analyze_weaknesses(cls, task_records: list) -> list:
        """分析学员薄弱项"""
        # 找出低分任务
        low_score_tasks = [t for t in task_records if t["score"] < 70]

        if not low_score_tasks:
            return []

        # 统计各薄弱类别
        weakness_scores = {}
        for wt in low_score_tasks:
            title = wt["title"].lower()
            for cat_id, cat_info in cls.WEAKNESS_CATEGORIES.items():
                if any(kw in title for kw in cat_info["keywords"]):
                    if cat_id not in weakness_scores:
                        weakness_scores[cat_id] = {
                            "count": 0,
                            "total_score": 0,
                            "tasks": [],
                        }
                    weakness_scores[cat_id]["count"] += 1
                    weakness_scores[cat_id]["total_score"] += wt["score"]
                    weakness_scores[cat_id]["tasks"].append(wt["title"])

        # 排序：按薄弱程度（低分优先）
        sorted_weaknesses = sorted(
            weakness_scores.items(),
            key=lambda x: x[1]["total_score"] / max(x[1]["count"], 1),
        )

        result = []
        for cat_id, data in sorted_weaknesses:
            cat_info = cls.WEAKNESS_CATEGORIES.get(cat_id, {})
            avg_score = data["total_score"] / max(data["count"], 1)
            result.append({
                "category": cat_info.get("label", cat_id),
                "description": f"在 {data['count']} 个相关任务中平均得分 {avg_score:.0f} 分",
                "score": int(avg_score),
                "suggestion": cat_info.get("suggestion", "建议加强相关领域学习"),
            })

        return result

    @classmethod
    def _build_improvement_plan(cls, weaknesses: list, avg_score: float) -> str:
        """生成能力提升方案"""
        if not weaknesses:
            return "当前实训成果良好，建议挑战更高难度的场景（如Web攻击溯源、内网渗透溯源）进一步提升实战能力。"

        plan_parts = []
        plan_parts.append("根据您的实训表现，建议按以下优先级进行能力提升：\n")

        for i, w in enumerate(weaknesses, 1):
            plan_parts.append(f"{i}. {w['category']}（当前平均分：{w['score']}分）")
            plan_parts.append(f"   提升建议：{w['suggestion']}")
            plan_parts.append("")

        if avg_score < 60:
            plan_parts.append("💡 建议从「日志基础认知」场景重新开始，打好基础后再挑战高级场景。")
        elif avg_score < 80:
            plan_parts.append("💡 建议针对性复习薄弱环节，每个场景至少拿到B级评价后再进入下一场景。")

        return "\n".join(plan_parts)

    @classmethod
    def _build_summary(cls, task_records: list, avg_score: float,
                       overall_grade: str, weaknesses: list) -> str:
        """生成实训总结"""
        total = len(task_records)
        passed = sum(1 for t in task_records if t["status"] == "passed")
        optimize = sum(1 for t in task_records if t["status"] == "optimize")
        retry = sum(1 for t in task_records if t["status"] == "retry")

        summary_parts = []
        summary_parts.append(f"本次实训共完成 {total} 个任务，综合评级 {overall_grade}。")
        summary_parts.append(f"  ✅ 通过（A级）：{passed} 个")
        summary_parts.append(f"  ⚠️ 待优化（B级）：{optimize} 个")
        summary_parts.append(f"  ❌ 需重做（C级）：{retry} 个")
        summary_parts.append(f"  平均得分：{avg_score:.1f} 分")
        summary_parts.append("")

        if overall_grade == "A":
            summary_parts.append("实训表现优秀！建议挑战更高难度的实战场景，如Web攻击溯源、内网渗透溯源。")
        elif overall_grade == "B":
            summary_parts.append("实训表现良好，仍有提升空间。建议针对薄弱项进行专项训练。")
        else:
            summary_parts.append("实训表现需加强，建议重新学习基础知识后再次尝试。")

        if weaknesses:
            summary_parts.append(f"\n需重点提升：{'、'.join(w['category'] for w in weaknesses[:3])}")

        return "\n".join(summary_parts)

    @staticmethod
    def _calc_overall_grade(avg_score: float) -> str:
        if avg_score >= 90:
            return "A"
        elif avg_score >= 70:
            return "B"
        return "C"