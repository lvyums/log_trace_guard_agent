"""
模块五：智能化任务下发引擎 — 自动加载场景资源、下发标准化实操任务

支持动态场景注入（DYN_ 前缀），供 log-correlate to-scenario 使用：
  - inject_scenario(): 注入一个由攻击链数据动态生成的场景
  - 动态场景会被 dispatch()、get_scenario()、get_standard_answer() 识别
"""

import time
from typing import Optional

from common.logger import LogManager
from common.json_util import JsonConfigLoader

logger = LogManager.get_logger()


class TaskEngine:
    """任务下发引擎 — 管理场景和任务的生命周期"""

    _scenarios_cache = None
    _answers_cache = None
    _session_records: dict[str, dict] = {}  # student_id -> {scenario_id -> {task_id -> [records]}}

    # 动态场景（由 to-scenario 注入，不持久化到 JSON）
    _dynamic_scenarios: list[dict] = []
    _dynamic_answers: dict[str, dict] = {}

    @classmethod
    def _load_scenarios(cls) -> list[dict]:
        """加载场景配置"""
        if cls._scenarios_cache is None:
            from app.settings import settings
            path = f"{settings.rule_data_dir}/training_scenarios.json"
            cls._scenarios_cache = JsonConfigLoader.load(path) or []
        return cls._scenarios_cache

    @classmethod
    def _load_answers(cls) -> dict:
        """加载标准答案库"""
        if cls._answers_cache is None:
            from app.settings import settings
            path = f"{settings.rule_data_dir}/training_standard_answers.json"
            cls._answers_cache = JsonConfigLoader.load(path) or {}
        return cls._answers_cache

    @classmethod
    def get_all_scenarios(cls) -> list[dict]:
        """获取所有场景（含动态场景）"""
        return cls._get_dynamic_scenarios() + cls._load_scenarios()

    @classmethod
    def get_scenario(cls, scenario_id: str) -> Optional[dict]:
        """获取单个场景（支持动态场景 DYN_ 前缀）"""
        # 优先查动态
        for s in cls._dynamic_scenarios:
            if s.get("scenario_id") == scenario_id:
                return s
        # 再查 JSON
        scenarios = cls._load_scenarios()
        for s in scenarios:
            if s["scenario_id"] == scenario_id:
                return s
        return None

    @classmethod
    def get_scenarios_by_category(cls, category: str) -> list[dict]:
        """按分类获取场景（含动态场景）"""
        scenarios = cls.get_all_scenarios()
        return [s for s in scenarios if s.get("category") == category]

    @classmethod
    def get_tasks(cls, scenario_id: str) -> list[dict]:
        """获取场景的所有任务"""
        scenario = cls.get_scenario(scenario_id)
        if scenario:
            return scenario.get("tasks", [])
        return []

    @classmethod
    def get_task(cls, scenario_id: str, task_id: str) -> Optional[dict]:
        """获取单个任务"""
        tasks = cls.get_tasks(scenario_id)
        for t in tasks:
            if t["task_id"] == task_id:
                return t
        return None

    @classmethod
    def get_standard_answer(cls, scenario_id: str, task_id: str) -> Optional[dict]:
        """获取标准答案（优先查动态，再查 JSON）"""
        # 查动态
        if scenario_id in cls._dynamic_answers:
            return cls._dynamic_answers[scenario_id].get(task_id)
        # 查 JSON
        answers = cls._load_answers()
        scenario_answers = answers.get(scenario_id, {})
        return scenario_answers.get(task_id)

    @classmethod
    def get_scenario_info(cls, scenario: dict) -> dict:
        """提取场景基本信息"""
        return {
            "scenario_id": scenario.get("scenario_id", ""),
            "name": scenario.get("name", ""),
            "category": scenario.get("category", ""),
            "difficulty": scenario.get("difficulty", ""),
            "order": scenario.get("order", 0),
            "description": scenario.get("description", ""),
            "objectives": scenario.get("objectives", []),
        }

    @classmethod
    def get_task_info(cls, task: dict) -> dict:
        """提取任务基本信息"""
        return {
            "task_id": task.get("task_id", ""),
            "order": task.get("order", 0),
            "title": task.get("title", ""),
            "description": task.get("description", ""),
            "input_type": task.get("input_type", ""),
            "input_data": task.get("input_data", []),
            "submit_type": task.get("submit_type", ""),
            "hint": task.get("hint"),
        }

    @classmethod
    def dispatch(cls, scenario_id: Optional[str] = None,
                 category: Optional[str] = None) -> list[dict]:
        """下发任务 — 返回场景+任务列表（支持动态场景）"""
        if scenario_id:
            scenario = cls.get_scenario(scenario_id)
            if not scenario:
                return []
            tasks = scenario.get("tasks", [])
            return [{
                "scenario": cls.get_scenario_info(scenario),
                "tasks": [cls.get_task_info(t) for t in tasks],
                "total_tasks": len(tasks),
                "completed_tasks": 0,
            }]

        if category:
            scenarios = cls.get_scenarios_by_category(category)
        else:
            scenarios = cls.get_all_scenarios()

        result = []
        for s in scenarios:
            tasks = s.get("tasks", [])
            result.append({
                "scenario": cls.get_scenario_info(s),
                "tasks": [cls.get_task_info(t) for t in tasks],
                "total_tasks": len(tasks),
                "completed_tasks": 0,
            })

        return result

    # ── 动态场景注入（供 log-correlate to-scenario 使用） ──

    @classmethod
    def inject_scenario(cls, scenario: dict, standard_answers: dict) -> str:
        """
        注入一个动态生成的场景到引擎中。
        注入后的场景可被 dispatch()、get_scenario()、get_standard_answer() 等访问。

        Args:
            scenario: { name, description, category, difficulty, objectives, tasks }
                其中 tasks 为 { task_id, title, description, input_type, submit_type, hint }
            standard_answers: { task_id: { ... 标准答案字段 } }

        Returns:
            注入的场景 ID（形如 DYN_1712345678_0）
        """
        scenario_id = f"DYN_{int(time.time())}_{len(cls._dynamic_scenarios)}"
        scenario["scenario_id"] = scenario_id

        cls._dynamic_scenarios.append(scenario)
        cls._dynamic_answers[scenario_id] = standard_answers or {}
        logger.info(
            f"动态场景已注入: {scenario_id} — {scenario.get('name', '?')}, "
            f"{len(scenario.get('tasks', []))} 个任务"
        )
        return scenario_id

    @classmethod
    def _get_dynamic_scenarios(cls) -> list[dict]:
        return list(cls._dynamic_scenarios)

    # ── 学员记录 ──

    @classmethod
    def record_submission(cls, student_id: str, scenario_id: str,
                          task_id: str, score: int, grade: str, status: str):
        """记录学员提交结果"""
        if student_id not in cls._session_records:
            cls._session_records[student_id] = {}

        if scenario_id not in cls._session_records[student_id]:
            cls._session_records[student_id][scenario_id] = {}

        if task_id not in cls._session_records[student_id][scenario_id]:
            cls._session_records[student_id][scenario_id][task_id] = []

        cls._session_records[student_id][scenario_id][task_id].append({
            "score": score,
            "grade": grade,
            "status": status,
            "attempt": len(cls._session_records[student_id][scenario_id][task_id]) + 1,
        })

    @classmethod
    def get_student_records(cls, student_id: str,
                            scenario_id: Optional[str] = None) -> dict:
        """获取学员记录"""
        if student_id not in cls._session_records:
            return {}

        if scenario_id:
            return cls._session_records[student_id].get(scenario_id, {})

        return cls._session_records[student_id]

    @classmethod
    def get_task_best_score(cls, student_id: str, scenario_id: str,
                            task_id: str) -> Optional[dict]:
        """获取某任务的最佳成绩"""
        records = cls._session_records.get(student_id, {}).get(scenario_id, {}).get(task_id, [])
        if not records:
            return None
        return max(records, key=lambda r: r["score"])
