"""
Module 5: Training / Assessment

Provides a complete training and assessment infrastructure:
  - TaskEngine: loads scenarios from JSON, dispatches tasks, records submissions
  - CheckStrategyFactory & strategies: evaluate student answers (rule, script,
    conclusion, plan)
  - ErrorAnalysis: generates Chinese-language error explanations
  - ReportGenerator: produces per-student / per-scenario performance reports
  - TrainingService: high-level API wrapping all of the above with Result
    responses.
"""

import json
import os
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type

from log_guard.common.utils import JsonConfigLoader, LogManager, Result

logger = LogManager.get_logger("training")

# Path where submission records are persisted
_SUBMISSIONS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "rule_data",
    "submissions.json",
)


# ---------------------------------------------------------------------------
# TaskEngine
# ---------------------------------------------------------------------------

class TaskEngine:
    """Loads training scenarios and standard answers, dispatches tasks, and
    records student submissions.

    Data sources (loaded via JsonConfigLoader):
        - training_scenarios.json
        - training_standard_answers.json

    Submissions are persisted to *submissions.json*.
    """

    def __init__(self) -> None:
        self._scenarios: List[dict] = []
        self._standard_answers: dict = {}
        self._load_data()

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _load_data(self) -> None:
        """Load scenarios and standard answers from JSON config files."""
        try:
            self._scenarios = JsonConfigLoader.load("training_scenarios.json")
            if not isinstance(self._scenarios, list):
                self._scenarios = []
        except Exception as exc:
            logger.warning(f"Failed to load training_scenarios.json: {exc}")
            self._scenarios = []

        try:
            self._standard_answers = JsonConfigLoader.load(
                "training_standard_answers.json"
            )
            if not isinstance(self._standard_answers, dict):
                self._standard_answers = {}
        except Exception as exc:
            logger.warning(f"Failed to load training_standard_answers.json: {exc}")
            self._standard_answers = {}

    # ------------------------------------------------------------------
    # dispatch
    # ------------------------------------------------------------------

    def dispatch(
        self, scenario_id: Optional[str] = None, category: Optional[str] = None
    ) -> List[dict]:
        """Return a list of scenario dicts matching the given filters.

        Args:
            scenario_id: If provided, only return that specific scenario.
            category: If provided, only return scenarios whose category
                matches (case-insensitive).

        Returns:
            A list of matching scenario dicts.  Each dict includes the
            scenario metadata and its tasks.
        """
        results: List[dict] = []

        for scenario in self._scenarios:
            sid = scenario.get("scenario_id", "")
            scat = scenario.get("category", "")

            if scenario_id and sid != scenario_id:
                continue
            if category and category.lower() != scat.lower():
                continue

            results.append(scenario)

        return results

    # ------------------------------------------------------------------
    # get_standard_answer
    # ------------------------------------------------------------------

    def get_standard_answer(
        self, scenario_id: str, task_id: str
    ) -> Optional[dict]:
        """Return the standard answer dict for the given task, or *None*.

        The returned dict includes the ``correct_answer`` fields,
        ``key_fields``, and ``scoring_rules``.
        """
        scenario_answers = self._standard_answers.get(scenario_id)
        if scenario_answers is None:
            return None
        return scenario_answers.get(task_id)

    # ------------------------------------------------------------------
    # get_task
    # ------------------------------------------------------------------

    def get_task(self, scenario_id: str, task_id: str) -> Optional[dict]:
        """Return the task dict for the given scenario + task ID, or *None*."""
        for scenario in self._scenarios:
            if scenario.get("scenario_id") == scenario_id:
                for task in scenario.get("tasks", []):
                    if task.get("task_id") == task_id:
                        return task
        return None

    # ------------------------------------------------------------------
    # record_submission
    # ------------------------------------------------------------------

    def record_submission(
        self,
        student_id: str,
        scenario_id: str,
        task_id: str,
        score: float,
        grade: str,
        status: str,
    ) -> None:
        """Append a submission record to ``submissions.json``.

        If the file does not exist it is created.  Each record is a dict
        with keys: ``student_id``, ``scenario_id``, ``task_id``, ``score``,
        ``grade``, ``status``, ``timestamp``.
        """
        records: List[dict] = []
        if os.path.exists(_SUBMISSIONS_FILE):
            try:
                with open(_SUBMISSIONS_FILE, "r", encoding="utf-8") as fh:
                    records = json.load(fh)
            except (json.JSONDecodeError, IOError) as exc:
                logger.warning(f"Failed to read submissions.json: {exc}")
                records = []

        import time

        records.append(
            {
                "student_id": student_id,
                "scenario_id": scenario_id,
                "task_id": task_id,
                "score": score,
                "grade": grade,
                "status": status,
                "timestamp": int(time.time() * 1000),
            }
        )

        os.makedirs(os.path.dirname(_SUBMISSIONS_FILE), exist_ok=True)
        with open(_SUBMISSIONS_FILE, "w", encoding="utf-8") as fh:
            json.dump(records, fh, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------
    # get_student_records
    # ------------------------------------------------------------------

    def get_student_records(
        self, student_id: str, scenario_id: Optional[str] = None
    ) -> List[dict]:
        """Return all submission records for a given student.

        Args:
            student_id: The student identifier.
            scenario_id: Optional — if provided, only return records for
                this scenario.

        Returns:
            A list of matching submission record dicts.
        """
        if not os.path.exists(_SUBMISSIONS_FILE):
            return []

        try:
            with open(_SUBMISSIONS_FILE, "r", encoding="utf-8") as fh:
                records: List[dict] = json.load(fh)
        except (json.JSONDecodeError, IOError):
            return []

        results = [r for r in records if r.get("student_id") == student_id]
        if scenario_id:
            results = [r for r in results if r.get("scenario_id") == scenario_id]
        return results


# ---------------------------------------------------------------------------
# BaseCheckStrategy  (abstract)
# ---------------------------------------------------------------------------

class BaseCheckStrategy(ABC):
    """Abstract base strategy for checking a student's answer against a
    standard answer."""

    strategy_type: str = "base"

    @abstractmethod
    def check(self, content: Any, standard: dict) -> dict:
        """Evaluate *content* against the *standard* answer.

        Args:
            content: The student-submitted content (varies by strategy).
            standard: The standard answer dict (from
                ``training_standard_answers.json``), expected to contain
                ``correct_answer``, ``key_fields``, and ``scoring_rules``.

        Returns:
            A dict with keys:
                - ``score`` (float, 0.0 – 100.0)
                - ``grade`` (str: ``"excellent"``, ``"good"``,
                  ``"pass"``, ``"fail"``)
                - ``passed`` (bool)
                - ``details`` (list of per-field match results)
                - ``match_rate`` (float)
        """
        ...


# ---------------------------------------------------------------------------
# Helper: scoring logic shared by strategies
# ---------------------------------------------------------------------------

def _grade_from_score(score: float) -> str:
    """Convert a numeric score (0-100) to a grade label."""
    if score >= 90:
        return "excellent"
    if score >= 75:
        return "good"
    if score >= 60:
        return "pass"
    return "fail"


def _fuzzy_match(text: str, acceptable_values: List[str]) -> bool:
    """Return True if *text* contains any of the *acceptable_values*
    (case-insensitive, substring match)."""
    text_lower = text.lower()
    for val in acceptable_values:
        if val.lower() in text_lower:
            return True
    return False


def _field_check(
    submitted: Any, key_fields: dict, field_name: str
) -> dict:
    """Check a single field against its acceptable values.

    Args:
        submitted: The value from the student's submission.
        key_fields: The ``key_fields`` dict from the standard answer.
        field_name: The field to check.

    Returns:
        A dict with ``field``, ``passed``, ``expected``, ``actual``.
    """
    acceptable = key_fields.get(field_name, [])
    if not acceptable:
        return {"field": field_name, "passed": True, "expected": acceptable, "actual": submitted}

    if isinstance(submitted, str):
        passed = _fuzzy_match(submitted, acceptable)
    elif isinstance(submitted, bool):
        passed = str(submitted).lower() in [a.lower() for a in acceptable]
    elif isinstance(submitted, (int, float)):
        passed = str(submitted) in [a.lower() for a in acceptable]
    elif isinstance(submitted, list):
        # Check if any list item matches any acceptable value
        joined = " ".join(str(item) for item in submitted)
        passed = _fuzzy_match(joined, acceptable)
    elif isinstance(submitted, dict):
        joined = json.dumps(submitted, ensure_ascii=False)
        passed = _fuzzy_match(joined, acceptable)
    else:
        passed = False

    return {
        "field": field_name,
        "passed": passed,
        "expected": acceptable,
        "actual": submitted,
    }


def _compute_score(
    details: List[dict],
    required_fields: List[str],
    min_match_rate: float,
    weight: float = 1.0,
) -> dict:
    """Compute the aggregate score, grade, and pass/fail status from
    per-field check results.

    Returns:
        dict with ``score``, ``grade``, ``passed``, ``match_rate``.
    """
    total = len(details)
    if total == 0:
        return {"score": 0.0, "grade": "fail", "passed": False, "match_rate": 0.0}

    passed_count = sum(1 for d in details if d["passed"])

    # Check that all required fields passed
    required_ok = True
    for d in details:
        if d["field"] in required_fields and not d["passed"]:
            required_ok = False
            break

    match_rate = passed_count / total
    # Score = match_rate * 100 * weight, capped at 100
    raw_score = match_rate * 100.0 * weight
    score = min(raw_score, 100.0)

    if not required_ok or match_rate < min_match_rate:
        passed = False
        # Cap score at 59 if required fields are missing
        if not required_ok:
            score = min(score, 59.0)
    else:
        passed = True

    grade = _grade_from_score(score)
    return {"score": round(score, 1), "grade": grade, "passed": passed, "match_rate": round(match_rate, 2)}


# ---------------------------------------------------------------------------
# RuleCheckStrategy
# ---------------------------------------------------------------------------

class RuleCheckStrategy(BaseCheckStrategy):
    """Check strategies for 'rule' type submissions (regex patterns,
    filter rules, etc.)."""

    strategy_type = "rule"

    def check(self, content: Any, standard: dict) -> dict:
        """Compare rule content (text) against the standard answer.

        The standard dict should contain:
            - ``correct_answer`` (dict with rule fields)
            - ``key_fields`` (dict mapping field names to acceptable values)
            - ``scoring_rules`` (dict with ``required_fields``,
              ``min_match_rate``, ``weight``)
        """
        if not isinstance(content, dict):
            content = {"content": str(content)}

        correct_answer = standard.get("correct_answer", {})
        key_fields = standard.get("key_fields", {})
        scoring_rules = standard.get("scoring_rules", {})

        required_fields = scoring_rules.get("required_fields", [])
        min_match_rate = scoring_rules.get("min_match_rate", 0.5)
        weight = scoring_rules.get("weight", 1.0)

        details: List[dict] = []
        for field_name, acceptable_values in key_fields.items():
            submitted_value = content.get(field_name, content.get("content", ""))
            details.append(
                _field_check(submitted_value, key_fields, field_name)
            )

        # Also check the content directly against the correct_answer
        if "content" not in key_fields and isinstance(correct_answer, dict):
            for corr_key, corr_val in correct_answer.items():
                if corr_key not in key_fields:
                    submitted_val = content.get(corr_key, "")
                    expected_str = str(corr_val) if not isinstance(corr_val, str) else corr_val
                    passed = _fuzzy_match(str(submitted_val), [expected_str])
                    details.append(
                        {
                            "field": corr_key,
                            "passed": passed,
                            "expected": [expected_str],
                            "actual": submitted_val,
                        }
                    )

        result = _compute_score(details, required_fields, min_match_rate, weight)
        result["details"] = details
        return result


# ---------------------------------------------------------------------------
# ScriptCheckStrategy
# ---------------------------------------------------------------------------

class ScriptCheckStrategy(BaseCheckStrategy):
    """Check strategies for 'script' type submissions (ES queries,
    syslog configurations, etc.)."""

    strategy_type = "script"

    def check(self, content: Any, standard: dict) -> dict:
        """Compare script content against the standard answer.

        The standard dict should contain:
            - ``correct_answer`` (dict with script fields)
            - ``key_fields`` (dict mapping field names to acceptable values)
            - ``scoring_rules``
        """
        if not isinstance(content, dict):
            content = {"content": str(content)}

        correct_answer = standard.get("correct_answer", {})
        key_fields = standard.get("key_fields", {})
        scoring_rules = standard.get("scoring_rules", {})

        required_fields = scoring_rules.get("required_fields", [])
        min_match_rate = scoring_rules.get("min_match_rate", 0.5)
        weight = scoring_rules.get("weight", 1.0)

        details: List[dict] = []

        # Check key_fields first
        for field_name, acceptable_values in key_fields.items():
            submitted_value = content.get(field_name, content.get("content", ""))
            details.append(
                _field_check(submitted_value, key_fields, field_name)
            )

        # Check correct_answer fields that are not already in key_fields
        if isinstance(correct_answer, dict):
            for corr_key, corr_val in correct_answer.items():
                if corr_key not in key_fields and corr_key != "reasoning":
                    submitted_val = content.get(corr_key, "")
                    expected_str = str(corr_val) if not isinstance(corr_val, str) else corr_val
                    # For script content, check if the submission contains key
                    # technical terms from the expected answer
                    passed = _fuzzy_match(str(submitted_val), [expected_str])
                    details.append(
                        {
                            "field": corr_key,
                            "passed": passed,
                            "expected": [expected_str],
                            "actual": submitted_val,
                        }
                    )

        # If the content is a raw string, do a keyword-based check
        if not details:
            raw_content = str(content.get("content", ""))
            if isinstance(correct_answer, dict):
                all_keywords = []
                for val in correct_answer.values():
                    if isinstance(val, str):
                        all_keywords.extend(val.split())
                keyword_matches = sum(
                    1 for kw in all_keywords if kw.lower() in raw_content.lower()
                )
                match_rate = (
                    keyword_matches / len(all_keywords) if all_keywords else 0
                )
                passed = match_rate >= min_match_rate
                score = round(match_rate * 100 * weight, 1)
                grade = _grade_from_score(score)
                return {
                    "score": min(score, 100.0),
                    "grade": grade,
                    "passed": passed,
                    "match_rate": round(match_rate, 2),
                    "details": [
                        {
                            "field": "content",
                            "passed": passed,
                            "expected": list(correct_answer.keys()),
                            "actual": "keyword_match",
                        }
                    ],
                }

        result = _compute_score(details, required_fields, min_match_rate, weight)
        result["details"] = details
        return result


# ---------------------------------------------------------------------------
# ConclusionCheckStrategy
# ---------------------------------------------------------------------------

class ConclusionCheckStrategy(BaseCheckStrategy):
    """Check strategies for 'conclusion' type submissions (analysis,
    judgment, evidence)."""

    strategy_type = "conclusion"

    def check(self, content: Any, standard: dict) -> dict:
        """Compare conclusion text against the standard answer.

        The standard dict should contain:
            - ``correct_answer`` (dict with conclusion fields)
            - ``key_fields`` (dict mapping field names to acceptable values)
            - ``scoring_rules``
        """
        if not isinstance(content, dict):
            content = {"content": str(content)}

        correct_answer = standard.get("correct_answer", {})
        key_fields = standard.get("key_fields", {})
        scoring_rules = standard.get("scoring_rules", {})

        required_fields = scoring_rules.get("required_fields", [])
        min_match_rate = scoring_rules.get("min_match_rate", 0.5)
        weight = scoring_rules.get("weight", 1.0)

        details: List[dict] = []

        # Check key_fields
        for field_name, acceptable_values in key_fields.items():
            submitted_value = content.get(field_name, content.get("content", ""))
            details.append(
                _field_check(submitted_value, key_fields, field_name)
            )

        # Check correct_answer fields that are not in key_fields
        if isinstance(correct_answer, dict):
            for corr_key, corr_val in correct_answer.items():
                if corr_key not in key_fields and corr_key != "reasoning":
                    submitted_val = content.get(corr_key, "")
                    expected_str = str(corr_val) if not isinstance(corr_val, str) else corr_val
                    if isinstance(corr_val, list):
                        # For lists like attack_chain, check if key items exist
                        combined = " ".join(
                            str(item) for item in corr_val
                        )
                        passed = _fuzzy_match(str(submitted_val), [combined])
                    else:
                        passed = _fuzzy_match(str(submitted_val), [expected_str])
                    details.append(
                        {
                            "field": corr_key,
                            "passed": passed,
                            "expected": [expected_str],
                            "actual": submitted_val,
                        }
                    )

        # If no structured fields, do a keyword-based check on the raw content
        if not details:
            raw_content = str(content.get("content", ""))
            if isinstance(correct_answer, dict):
                reasoning = correct_answer.get("reasoning", "")
                # Combine all values into a keyword set
                all_text = " ".join(
                    str(v) for v in correct_answer.values() if isinstance(v, str)
                )
                keywords = [
                    w for w in all_text.split() if len(w) > 2
                ]
                unique_keywords = list(set(keywords))
                keyword_matches = sum(
                    1 for kw in unique_keywords if kw.lower() in raw_content.lower()
                )
                match_rate = (
                    keyword_matches / len(unique_keywords)
                    if unique_keywords
                    else 0
                )
                passed = match_rate >= min_match_rate
                score = round(match_rate * 100 * weight, 1)
                grade = _grade_from_score(score)
                return {
                    "score": min(score, 100.0),
                    "grade": grade,
                    "passed": passed,
                    "match_rate": round(match_rate, 2),
                    "details": [
                        {
                            "field": "content",
                            "passed": passed,
                            "expected": list(correct_answer.keys()),
                            "actual": "keyword_match",
                        }
                    ],
                }

        result = _compute_score(details, required_fields, min_match_rate, weight)
        result["details"] = details
        return result


# ---------------------------------------------------------------------------
# PlanCheckStrategy
# ---------------------------------------------------------------------------

class PlanCheckStrategy(BaseCheckStrategy):
    """Check strategies for 'plan' type submissions (architecture plans,
    remediation steps, budget proposals)."""

    strategy_type = "plan"

    def check(self, content: Any, standard: dict) -> dict:
        """Compare plan content against the standard answer.

        The standard dict should contain:
            - ``correct_answer`` (dict with plan fields)
            - ``key_fields`` (dict mapping field names to acceptable values)
            - ``scoring_rules``
        """
        if not isinstance(content, dict):
            content = {"content": str(content)}

        correct_answer = standard.get("correct_answer", {})
        key_fields = standard.get("key_fields", {})
        scoring_rules = standard.get("scoring_rules", {})

        required_fields = scoring_rules.get("required_fields", [])
        min_match_rate = scoring_rules.get("min_match_rate", 0.4)
        weight = scoring_rules.get("weight", 1.0)

        details: List[dict] = []

        # Check key_fields
        for field_name, acceptable_values in key_fields.items():
            submitted_value = content.get(field_name, content.get("content", ""))
            details.append(
                _field_check(submitted_value, key_fields, field_name)
            )

        # Check correct_answer fields not in key_fields
        if isinstance(correct_answer, dict):
            for corr_key, corr_val in correct_answer.items():
                if corr_key not in key_fields and corr_key != "reasoning":
                    submitted_val = content.get(corr_key, "")
                    expected_str = str(corr_val) if not isinstance(corr_val, str) else corr_val
                    if isinstance(corr_val, list):
                        combined = " ".join(
                            str(item) for item in corr_val
                        )
                        passed = _fuzzy_match(str(submitted_val), [combined])
                    else:
                        passed = _fuzzy_match(str(submitted_val), [expected_str])
                    details.append(
                        {
                            "field": corr_key,
                            "passed": passed,
                            "expected": [expected_str],
                            "actual": submitted_val,
                        }
                    )

        # If no structured content, do keyword-based check
        if not details:
            raw_content = str(content.get("content", ""))
            if isinstance(correct_answer, dict):
                all_text = " ".join(
                    str(v) for v in correct_answer.values() if isinstance(v, str)
                )
                keywords = [w for w in all_text.split() if len(w) > 2]
                unique_keywords = list(set(keywords))
                keyword_matches = sum(
                    1 for kw in unique_keywords if kw.lower() in raw_content.lower()
                )
                match_rate = (
                    keyword_matches / len(unique_keywords)
                    if unique_keywords
                    else 0
                )
                passed = match_rate >= min_match_rate
                score = round(match_rate * 100 * weight, 1)
                grade = _grade_from_score(score)
                return {
                    "score": min(score, 100.0),
                    "grade": grade,
                    "passed": passed,
                    "match_rate": round(match_rate, 2),
                    "details": [
                        {
                            "field": "content",
                            "passed": passed,
                            "expected": list(correct_answer.keys()),
                            "actual": "keyword_match",
                        }
                    ],
                }

        result = _compute_score(details, required_fields, min_match_rate, weight)
        result["details"] = details
        return result


# ---------------------------------------------------------------------------
# CheckStrategyFactory
# ---------------------------------------------------------------------------

class CheckStrategyFactory:
    """Factory for registering and retrieving check strategies.

    Maintains a registry of strategy classes keyed by strategy type name
    (``rule``, ``script``, ``conclusion``, ``plan``).
    """

    def __init__(self) -> None:
        self._strategies: Dict[str, Type[BaseCheckStrategy]] = {}
        self._instances: Dict[str, BaseCheckStrategy] = {}

    def register(self, name: str, strategy_cls: Type[BaseCheckStrategy]) -> None:
        """Register a strategy class under the given name."""
        self._strategies[name] = strategy_cls

    def get_strategy(self, name: str) -> Optional[BaseCheckStrategy]:
        """Get or create a strategy instance by name."""
        if name in self._instances:
            return self._instances[name]

        cls = self._strategies.get(name)
        if cls is None:
            return None

        instance = cls()
        self._instances[name] = instance
        return instance

    @property
    def registered_types(self) -> List[str]:
        """Return list of registered strategy type names."""
        return list(self._strategies.keys())


# ---- Default strategies registration ----

_default_check_factory: Optional[CheckStrategyFactory] = None


def _register_default_check_strategies() -> CheckStrategyFactory:
    """Create the default factory and register all built-in strategies."""
    factory = CheckStrategyFactory()
    factory.register("rule", RuleCheckStrategy)
    factory.register("script", ScriptCheckStrategy)
    factory.register("conclusion", ConclusionCheckStrategy)
    factory.register("plan", PlanCheckStrategy)
    return factory


def get_default_check_factory() -> CheckStrategyFactory:
    """Get or create the default check strategy factory."""
    global _default_check_factory
    if _default_check_factory is None:
        _default_check_factory = _register_default_check_strategies()
    return _default_check_factory


# Register at module level
_default_check_factory = _register_default_check_strategies()


# ---------------------------------------------------------------------------
# ErrorAnalysis
# ---------------------------------------------------------------------------

class ErrorAnalysis:
    """Generates Chinese-language error explanations based on the check
    results and task metadata."""

    # Mapping of common error patterns to Chinese explanations
    _ERROR_TEMPLATES = {
        "missing_required_field": "缺少关键字段「{field}」，该字段是{task_type}的核心组成部分",
        "low_match_rate": "答案与标准答案匹配度不足（{match_rate}），建议加强对{task_type}的理解",
        "incorrect_judgment": "判断结论有误，{task_type}的正确判断应为{expected}",
        "insufficient_evidence": "证据不充分，需要更详细的{task_type}分析支撑结论",
        "format_error": "答案格式不符合要求，{task_type}应包含{expected_format}字段",
        "keyword_missing": "缺少关键术语「{keyword}」，该术语在{task_type}中至关重要",
        "score_too_low": "得分偏低（{score}分），建议重新学习{task_type}相关内容",
    }

    def analyze(
        self,
        task_type: str,
        submit_type: str,
        task_title: str,
        checks: dict,
        score: float,
        grade: str,
    ) -> str:
        """Generate a Chinese-language error explanation.

        Args:
            task_type: The type of task (e.g., ``"日志类型识别"``).
            submit_type: The submission type (``rule``, ``script``,
                ``conclusion``, ``plan``).
            task_title: The title of the task.
            checks: The result dict returned by the check strategy.
            score: The numeric score (0-100).
            grade: The grade label.

        Returns:
            A Chinese-language explanation string.
        """
        if grade == "excellent":
            return f"【{task_title}】表现优秀！答案准确完整，得分为{score}分。"

        if grade == "good":
            return (
                f"【{task_title}】基本正确，得分{score}分。"
                f"部分细节可以进一步完善，建议对照标准答案检查遗漏点。"
            )

        if grade == "pass":
            return (
                f"【{task_title}】勉强通过，得分{score}分。"
                f"答案中存在较多不足，需要重点加强{task_type}相关内容的学习。"
            )

        # grade == "fail" — generate detailed error explanation
        reasons: List[str] = []

        # Check for missing required fields
        details = checks.get("details", [])
        match_rate = checks.get("match_rate", 0.0)

        for d in details:
            if not d.get("passed"):
                field = d.get("field", "")
                reasons.append(
                    self._ERROR_TEMPLATES["missing_required_field"].format(
                        field=field, task_type=task_type
                    )
                )

        if not reasons:
            if match_rate < 0.3:
                reasons.append(
                    self._ERROR_TEMPLATES["low_match_rate"].format(
                        match_rate=f"{match_rate:.0%}", task_type=task_type
                    )
                )
            elif score < 40:
                reasons.append(
                    self._ERROR_TEMPLATES["score_too_low"].format(
                        score=score, task_type=task_type
                    )
                )
            else:
                reasons.append(
                    f"答案与{task_type}的标准要求存在差异，建议重新审题并补充详细分析。"
                )

        explanation = (
            f"【{task_title}】未通过（{score}分，{grade}）。\n"
            + "\n".join(f"  - {r}" for r in reasons[:5])
        )
        if submit_type:
            explanation += (
                f"\n\n答题类型：{submit_type}。"
                f"请确保提交内容符合该类型的格式要求。"
            )

        return explanation


# ---------------------------------------------------------------------------
# ReportGenerator
# ---------------------------------------------------------------------------

class ReportGenerator:
    """Generates per-student, per-scenario performance reports."""

    def __init__(
        self,
        task_engine: Optional[TaskEngine] = None,
        check_factory: Optional[CheckStrategyFactory] = None,
    ) -> None:
        self._task_engine = task_engine or TaskEngine()
        self._check_factory = check_factory or get_default_check_factory()

    # ------------------------------------------------------------------
    # generate_report
    # ------------------------------------------------------------------

    def generate_report(
        self, student_id: str, scenario_id: str
    ) -> dict:
        """Generate a comprehensive performance report for a student in a
        given scenario.

        The report includes:
            - ``student_info``: student ID and scenario metadata
            - ``total_tasks``: number of tasks in the scenario
            - ``submitted_count``: how many tasks the student submitted
            - ``average_score``: average score across submitted tasks
            - ``grade_distribution``: counts per grade level
            - ``task_results``: list of per-task results
            - ``overall_grade``: aggregate grade

        Args:
            student_id: The student identifier.
            scenario_id: The scenario identifier.

        Returns:
            A dict with the report structure described above.
        """
        # Get scenario metadata
        scenarios = self._task_engine.dispatch(scenario_id=scenario_id)
        if not scenarios:
            return {
                "student_info": {"student_id": student_id, "scenario_id": scenario_id},
                "error": f"Scenario {scenario_id!r} not found",
            }

        scenario = scenarios[0]
        tasks = scenario.get("tasks", [])

        # Get student submission records
        records = self._task_engine.get_student_records(student_id, scenario_id)
        records_by_task: Dict[str, dict] = {}
        for rec in records:
            tid = rec.get("task_id", "")
            # Keep the latest submission for each task
            if tid not in records_by_task:
                records_by_task[tid] = rec

        # Build per-task results
        task_results: List[dict] = []
        for task in tasks:
            task_id = task.get("task_id", "")
            record = records_by_task.get(task_id)
            task_results.append(
                {
                    "task_id": task_id,
                    "title": task.get("title", ""),
                    "order": task.get("order", 0),
                    "submit_type": task.get("submit_type", ""),
                    "submitted": record is not None,
                    "score": record.get("score", 0.0) if record else 0.0,
                    "grade": record.get("grade", "unsubmitted") if record else "unsubmitted",
                    "status": record.get("status", "pending") if record else "pending",
                }
            )

        submitted_results = [r for r in task_results if r["submitted"]]

        # Calculate statistics
        total_tasks = len(tasks)
        submitted_count = len(submitted_results)

        if submitted_count > 0:
            scores = [r["score"] for r in submitted_results]
            average_score = round(sum(scores) / len(scores), 1)
        else:
            average_score = 0.0

        # Grade distribution
        grade_dist: Dict[str, int] = {}
        for r in submitted_results:
            g = r["grade"]
            grade_dist[g] = grade_dist.get(g, 0) + 1

        # Overall grade
        if submitted_count == 0:
            overall_grade = "unsubmitted"
        elif average_score >= 90:
            overall_grade = "excellent"
        elif average_score >= 75:
            overall_grade = "good"
        elif average_score >= 60:
            overall_grade = "pass"
        else:
            overall_grade = "fail"

        return {
            "student_info": {
                "student_id": student_id,
                "scenario_id": scenario_id,
                "scenario_name": scenario.get("name", ""),
                "scenario_category": scenario.get("category", ""),
                "scenario_difficulty": scenario.get("difficulty", ""),
            },
            "total_tasks": total_tasks,
            "submitted_count": submitted_count,
            "average_score": average_score,
            "grade_distribution": grade_dist,
            "task_results": task_results,
            "overall_grade": overall_grade,
        }


# ---------------------------------------------------------------------------
# TrainingService
# ---------------------------------------------------------------------------

class TrainingService:
    """High-level service for training / assessment operations.

    Wraps TaskEngine, CheckStrategyFactory, ErrorAnalysis, and
    ReportGenerator behind a clean API that returns ``Result`` dicts.
    """

    def __init__(
        self,
        task_engine: Optional[TaskEngine] = None,
        check_factory: Optional[CheckStrategyFactory] = None,
        error_analysis: Optional[ErrorAnalysis] = None,
        report_generator: Optional[ReportGenerator] = None,
    ) -> None:
        self._task_engine = task_engine or TaskEngine()
        self._check_factory = check_factory or get_default_check_factory()
        self._error_analysis = error_analysis or ErrorAnalysis()
        self._report_generator = report_generator or ReportGenerator(
            task_engine=self._task_engine, check_factory=self._check_factory
        )

    # ------------------------------------------------------------------
    # dispatch_tasks
    # ------------------------------------------------------------------

    def dispatch_tasks(
        self,
        scenario_id: Optional[str] = None,
        category: Optional[str] = None,
    ) -> dict:
        """Dispatch training scenarios/tasks.

        Args:
            scenario_id: Optional filter by scenario ID.
            category: Optional filter by category (``basic``,
                ``collection``, ``filtering``, ``web_attack``,
                ``lateral_movement``, ``compliance``).

        Returns:
            A ``Result`` dict containing the list of matching scenarios.
        """
        try:
            scenarios = self._task_engine.dispatch(scenario_id, category)
            if not scenarios:
                return Result.fail(
                    msg="No matching scenarios found",
                    code=404,
                )
            return Result.ok(
                data={"scenarios": scenarios, "count": len(scenarios)},
                msg=f"Dispatched {len(scenarios)} scenario(s)",
            )
        except Exception as e:
            logger.error(f"dispatch_tasks failed: {e}", exc_info=True)
            return Result.from_exception(500, f"dispatch_tasks failed: {e}")

    # ------------------------------------------------------------------
    # submit_answer
    # ------------------------------------------------------------------

    def submit_answer(
        self,
        scenario_id: str,
        task_id: str,
        submit_type: str,
        content: Any,
        student_id: str,
    ) -> dict:
        """Submit an answer for evaluation.

        The method:
            1. Retrieves the standard answer and task metadata.
            2. Picks the appropriate check strategy based on ``submit_type``.
            3. Runs the check and computes a score and grade.
            4. Runs error analysis to generate a Chinese explanation.
            5. Records the submission to ``submissions.json``.
            6. Returns a ``Result`` with the evaluation outcome.

        Args:
            scenario_id: The scenario identifier.
            task_id: The task identifier.
            submit_type: The type of submission (``rule``, ``script``,
                ``conclusion``, ``plan``).
            content: The student's answer content.
            student_id: The student identifier.

        Returns:
            A ``Result`` dict with:
                - ``score``: numeric score (0-100)
                - ``grade``: grade label
                - ``status``: ``"pass"`` or ``"fail"``
                - ``checks``: detailed per-field check results
                - ``analysis``: Chinese-language explanation
                - ``suggestion``: improvement suggestion
                - ``task_title``: the task title
        """
        try:
            # Validate submit_type
            valid_types = ["rule", "script", "conclusion", "plan"]
            if submit_type not in valid_types:
                return Result.fail(
                    msg=f"Invalid submit_type '{submit_type}'. Must be one of {valid_types}",
                    code=400,
                )

            # Get task metadata
            task = self._task_engine.get_task(scenario_id, task_id)
            if task is None:
                return Result.fail(
                    msg=f"Task {task_id!r} not found in scenario {scenario_id!r}",
                    code=404,
                )

            task_title = task.get("title", "")
            task_type = task.get("description", "")[:50]

            # Get standard answer
            standard = self._task_engine.get_standard_answer(scenario_id, task_id)
            if standard is None:
                return Result.fail(
                    msg=f"Standard answer not found for {scenario_id}/{task_id}",
                    code=404,
                )

            # Get the appropriate check strategy
            strategy = self._check_factory.get_strategy(submit_type)
            if strategy is None:
                return Result.fail(
                    msg=f"Check strategy '{submit_type}' not available",
                    code=500,
                )

            # Run the check
            checks = strategy.check(content, standard)
            score = checks.get("score", 0.0)
            grade = checks.get("grade", "fail")
            passed = checks.get("passed", False)
            status = "pass" if passed else "fail"

            # Generate error analysis
            analysis = self._error_analysis.analyze(
                task_type=task_type,
                submit_type=submit_type,
                task_title=task_title,
                checks=checks,
                score=score,
                grade=grade,
            )

            # Generate suggestion
            if passed:
                suggestion = "答案正确，继续保持！"
            else:
                suggestion = self._generate_suggestion(
                    grade, score, submit_type, checks
                )

            # Record the submission
            self._task_engine.record_submission(
                student_id=student_id,
                scenario_id=scenario_id,
                task_id=task_id,
                score=score,
                grade=grade,
                status=status,
            )

            return Result.ok(
                data={
                    "score": score,
                    "grade": grade,
                    "status": status,
                    "checks": checks,
                    "analysis": analysis,
                    "suggestion": suggestion,
                    "task_title": task_title,
                    "task_id": task_id,
                    "scenario_id": scenario_id,
                },
                msg=f"Task {task_id} evaluated: {status} (score={score}, grade={grade})",
            )

        except Exception as e:
            logger.error(f"submit_answer failed: {e}", exc_info=True)
            return Result.from_exception(500, f"submit_answer failed: {e}")

    # ------------------------------------------------------------------
    # generate_report
    # ------------------------------------------------------------------

    def generate_report(self, student_id: str, scenario_id: str) -> dict:
        """Generate a performance report for a student in a scenario.

        Args:
            student_id: The student identifier.
            scenario_id: The scenario identifier.

        Returns:
            A ``Result`` dict containing the full report.
        """
        try:
            report = self._report_generator.generate_report(student_id, scenario_id)
            if "error" in report:
                return Result.fail(msg=report["error"], code=404)

            return Result.ok(
                data=report,
                msg=(
                    f"Report for {student_id} / {scenario_id}: "
                    f"{report.get('submitted_count', 0)}/{report.get('total_tasks', 0)} tasks "
                    f"submitted, avg score {report.get('average_score', 0.0)}"
                ),
            )

        except Exception as e:
            logger.error(f"generate_report failed: {e}", exc_info=True)
            return Result.from_exception(500, f"generate_report failed: {e}")

    # ------------------------------------------------------------------
    # _generate_suggestion  (internal helper)
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_suggestion(grade: str, score: float, submit_type: str, checks: dict) -> str:
        """Generate a Chinese-language improvement suggestion."""
        details = checks.get("details", [])
        failed_fields = [d["field"] for d in details if not d.get("passed")]

        if grade == "excellent":
            return "答案非常优秀，建议继续学习下一章节内容。"

        if grade == "good":
            if failed_fields:
                return (
                    f"总体表现良好，但以下字段可以进一步优化："
                    f"{'、'.join(failed_fields[:3])}。"
                    f"建议参照标准答案完善细节。"
                )
            return "基本正确，建议加强细节把握。"

        if grade == "pass":
            if failed_fields:
                return (
                    f"需要重点改进以下方面：{'、'.join(failed_fields[:3])}。"
                    f"建议重新学习相关知识点后再次作答。"
                )
            return "勉强通过，建议重新学习本任务相关知识点。"

        # fail
        if not failed_fields:
            return (
                f"得分偏低（{score}分），建议重新审题，"
                f"确保答案完整覆盖题目要求的所有要点。"
            )
        return (
            f"以下字段未通过检查：{'、'.join(failed_fields[:5])}。"
            f"建议对照标准答案逐项核对，补充缺失内容。"
        )