"""模块五：双维度智能纠错引擎 — 抽象基类 + 工厂 + 校验策略实现

采用「规则精准匹配 + 语义相似度比对」双校验机制：
- 规则匹配：检查必填字段、关键字段值是否命中
- 语义相似度：基于关键词重叠率计算文本语义相似度
- LLM 增强：当关键词匹配进入"灰色地带"时，调用 LLM 做语义理解评分
"""

from abc import ABC, abstractmethod
from typing import Optional, Type
from difflib import SequenceMatcher

from common.logger import LogManager
from common.json_util import JsonConfigLoader

logger = LogManager.get_logger()

# ── 评分阈值常量（从设计文档） ──
SIMILARITY_PASS = 0.85       # ≥0.85 正确
SIMILARITY_PARTIAL = 0.70    # 0.70-0.84 部分正确
RULE_MATCH_FULL = 1.0        # 100% 完全匹配
RULE_MATCH_PARTIAL = 0.6     # ≥60% 字段命中 → 部分遗漏
SCORE_A = 90                 # A级分数线
SCORE_B = 70                 # B级分数线
SCORE_C = 50                 # C级分数线

# ── LLM 增强评分阈值 ──
LLM_SCORE_LOWER = 60         # LLM 介入下限：低于此直接判定，不调LLM
LLM_SCORE_UPPER = 88         # LLM 介入上限：高于此直接A级，不调LLM


class BaseCheckStrategy(ABC):
    """校验策略基类"""

    strategy_type: str = "unknown"
    strategy_name: str = "unknown"

    @abstractmethod
    async def check(self, submission: dict, standard: dict) -> dict:
        """执行校验，返回 {checks, score, analysis}"""
        ...

    # ── LLM 增强评分（子类可覆盖） ──

    async def llm_enhance(self, submission: dict, standard: dict,
                          keyword_score: int) -> Optional[int]:
        """当关键词匹配在灰色地带时，调用 LLM 做语义评分

        仅在 keyword_score 处于 [LLM_SCORE_LOWER, LLM_SCORE_UPPER) 范围时调用。
        返回 LLM 评出的分数，或 None（表示不使用 LLM 结果）。
        """
        if not (LLM_SCORE_LOWER <= keyword_score < LLM_SCORE_UPPER):
            return None
        return await LLMCheckHelper.semantic_score(submission, standard)


class LLMCheckHelper:
    """LLM 语义评分助手 — 集中管理 LLM 调用，避免重复代码"""

    @staticmethod
    async def semantic_score(submission: dict, standard: dict) -> Optional[int]:
        """调用 LLM 对学员答案做语义评分

        比较学员答案与标准答案的语义相似度，返回调整后的分数。
        """
        try:
            from core.ai_base.llm_factory import LLMFactory
            from core.ai_base.prompt_manager import PromptManager
            from app.settings import settings

            if not settings.llm_api_key:
                return None

            # 提取提交内容
            sub_text = LLMCheckHelper._flatten(submission)
            std_text = LLMCheckHelper._flatten(standard.get("correct_answer", {}))

            if not sub_text or not std_text:
                return None

            prompt = PromptManager.get_prompt(
                "training_scoring",
                submission=sub_text[:2000],
                standard=std_text[:2000],
            )

            llm = await LLMFactory.get_main_llm()
            result = await llm.chat([
                {"role": "system",
                 "content": "你是一个公正的安全实训评分助理。只返回JSON，不要包含其他文字。"},
                {"role": "user", "content": prompt},
            ], timeout=15)

            if not result.get("success"):
                return None

            import json, re
            content = result["content"]
            # 提取 JSON
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if not json_match:
                return None

            parsed = json.loads(json_match.group())
            llm_score = parsed.get("overall_score")
            if isinstance(llm_score, (int, float)):
                return max(0, min(100, int(llm_score)))

            return None
        except Exception as e:
            logger.warning(f"LLM 评分调用失败: {e}")
            return None

    @staticmethod
    def _flatten(data: dict) -> str:
        """将字典展平为可读文本"""
        parts = []
        for key, val in data.items():
            if isinstance(val, list):
                parts.append(f"{key}: {', '.join(str(v) for v in val)}")
            elif isinstance(val, dict):
                parts.append(f"{key}: {LLMCheckHelper._flatten(val)}")
            else:
                parts.append(f"{key}: {val}")
        return "\n".join(parts)


class CheckStrategyFactory:
    """校验策略工厂 — 注册模式"""

    _strategies: dict[str, Type[BaseCheckStrategy]] = {}

    @classmethod
    def register(cls, strategy_type: str, strategy_cls: Type[BaseCheckStrategy]):
        cls._strategies[strategy_type] = strategy_cls
        logger.info(f"注册校验策略: {strategy_type} -> {strategy_cls.__name__}")

    @classmethod
    def get_strategy(cls, strategy_type: str) -> Optional[BaseCheckStrategy]:
        strategy_cls = cls._strategies.get(strategy_type)
        if strategy_cls:
            return strategy_cls()
        return None

    @classmethod
    def get_all_types(cls) -> list[str]:
        return list(cls._strategies.keys())


# ── 结论类校验策略（conclusion） ──

class ConclusionCheckStrategy(BaseCheckStrategy):
    """结论校验 — 检查关键字段匹配度"""

    strategy_type = "conclusion"
    strategy_name = "结论校验"

    async def check(self, submission: dict, standard: dict) -> dict:
        """结论校验 — 检查关键字段匹配度"""
        key_fields = standard.get("key_fields", {})
        scoring_rules = standard.get("scoring_rules", {})
        correct_answer = standard.get("correct_answer", {})
        required = scoring_rules.get("required_fields", [])
        min_match = scoring_rules.get("min_match_rate", 0.6)
        weight = scoring_rules.get("weight", 1.0)

        checks = []
        matched_count = 0
        total_checked = 0

        # 支持自由文本格式 (user_answer): 用全文关键词匹配
        user_answer = submission.get("user_answer")
        is_free_text = user_answer is not None

        if is_free_text:
            user_answer_str = str(user_answer).lower().strip()
            for field, expected_values in key_fields.items():
                total_checked += 1
                expected = correct_answer.get(field, "")
                expected_str = str(expected).lower().strip() if expected else ""

                # 全文关键词匹配
                hits = sum(1 for kw in expected_values if kw.lower() in user_answer_str)
                match_rate = hits / max(len(expected_values), 1)

                if match_rate >= SIMILARITY_PASS:
                    matched_count += 1
                    checks.append({
                        "field": field,
                        "status": "correct",
                        "expected": expected_str[:100],
                        "actual": user_answer_str[:100],
                        "detail": f"关键词 '{expected_values[0]}' 在答案中被识别",
                    })
                elif match_rate >= SIMILARITY_PARTIAL:
                    matched_count += 0.5
                    checks.append({
                        "field": field,
                        "status": "partial",
                        "expected": expected_str[:100],
                        "actual": user_answer_str[:100],
                        "detail": f"部分匹配，命中 {hits}/{len(expected_values)} 个关键词",
                    })
                else:
                    checks.append({
                        "field": field,
                        "status": "incorrect",
                        "expected": expected_str[:100],
                        "actual": user_answer_str[:80],
                        "detail": f"未识别到关键词: {expected_values}",
                    })
        else:
            for field, expected_values in key_fields.items():
                user_value = submission.get(field)
                if user_value is None:
                    continue

                total_checked += 1
                user_str = str(user_value).lower().strip()
                expected = correct_answer.get(field, "")
                expected_str = str(expected).lower().strip() if expected else ""

                # 规则匹配：检查用户值是否命中期望关键词
                is_match = any(
                    kw.lower() in user_str for kw in expected_values
                )

                if is_match:
                    matched_count += 1
                    checks.append({
                        "field": field,
                        "status": "correct",
                        "expected": str(expected_values[0]) if expected_values else "",
                        "actual": user_str[:100],
                        "detail": "字段匹配正确",
                    })
                else:
                    # 语义相似度作为辅助
                    similarity = SequenceMatcher(None, user_str, expected_str).ratio()
                    if similarity >= SIMILARITY_PARTIAL:
                        matched_count += 0.5
                        checks.append({
                            "field": field,
                            "status": "partial",
                            "expected": expected_str[:100],
                            "actual": user_str[:100],
                            "detail": f"部分匹配，语义相似度 {similarity:.0%}",
                        })
                    else:
                        checks.append({
                            "field": field,
                            "status": "incorrect",
                            "expected": expected_str[:100],
                            "actual": user_str[:100],
                            "detail": f"字段不匹配，期望包含关键词: {expected_values}",
                        })

        # 计算得分
        match_rate = matched_count / max(total_checked, 1)
        score = int(match_rate * 100 * weight)
        score = min(100, max(0, score))

        # LLM 增强：关键词匹配在灰色地带时做语义评分
        llm_adjusted = await self.llm_enhance(submission, standard, score)
        if llm_adjusted is not None:
            # 取关键词评分和 LLM 评分的加权平均（LLM 权重 0.4）
            score = int(score * 0.6 + llm_adjusted * 0.4)
            score = min(100, max(0, score))

        # 分析
        analysis = self._build_analysis(checks, match_rate, required)

        suggestion = None
        if score < SCORE_B:
            suggestion = "建议参考hint提示重新作答，注意关键字段的完整性"

        return {
            "checks": checks,
            "score": score,
            "grade": self._calc_grade(score),
            "status": self._calc_status(score),
            "analysis": analysis,
            "suggestion": suggestion,
            "correct_answer": correct_answer if score < SCORE_B else None,
        }

    def _build_analysis(self, checks: list, match_rate: float, required: list) -> str:
        incorrect = [c for c in checks if c["status"] == "incorrect"]
        partial = [c for c in checks if c["status"] == "partial"]

        lines = []
        if not incorrect and not partial:
            lines.append("回答正确！所有字段均匹配标准答案。")
            return "\n".join(lines)

        if incorrect:
            lines.append(f"以下字段存在错误（共 {len(incorrect)} 项）：")
            for c in incorrect:
                lines.append(f"  - {c['field']}：期望包含「{c['expected']}」，实际为「{c['actual']}」")
            lines.append("")

        if partial:
            lines.append(f"以下字段部分匹配（共 {len(partial)} 项）：")
            for c in partial:
                lines.append(f"  - {c['field']}：{c['detail']}")
            lines.append("")

        if match_rate < RULE_MATCH_PARTIAL:
            lines.append("❌ 核心字段缺失较多，建议重新学习相关知识点后作答。")
        elif match_rate < SIMILARITY_PARTIAL:
            lines.append("⚠️ 部分字段命中但不够完整，建议补充细节后再次提交。")

        return "\n".join(lines)

    @staticmethod
    def _calc_grade(score: int) -> str:
        if score >= SCORE_A:
            return "A"
        elif score >= SCORE_B:
            return "B"
        return "C"

    @staticmethod
    def _calc_status(score: int) -> str:
        if score >= SCORE_A:
            return "passed"
        elif score >= SCORE_B:
            return "optimize"
        return "retry"


# ── 规则类校验策略（rule） ──

class RuleCheckStrategy(BaseCheckStrategy):
    """规则校验 — 检查正则/过滤规则的正确性"""

    strategy_type = "rule"
    strategy_name = "规则校验"

    async def check(self, submission: dict, standard: dict) -> dict:
        """规则校验 — 检查正则/过滤规则的正确性"""
        key_fields = standard.get("key_fields", {})
        scoring_rules = standard.get("scoring_rules", {})
        correct_answer = standard.get("correct_answer", {})
        required = scoring_rules.get("required_fields", [])
        weight = scoring_rules.get("weight", 1.0)

        checks = []
        matched_count = 0
        total_checked = 0
        submission_text = str(submission).lower()

        # 检查规则字段
        for field, expected_values in key_fields.items():
            user_value = submission.get(field)
            if user_value is None:
                continue

            total_checked += 1
            user_str = str(user_value).lower().strip()
            expected_str = str(correct_answer.get(field, "")).lower().strip()

            # 关键词命中检查
            hits = sum(1 for kw in expected_values if kw.lower() in user_str)
            match_rate = hits / max(len(expected_values), 1)

            if match_rate >= SIMILARITY_PASS:
                matched_count += 1
                checks.append({
                    "field": field,
                    "status": "correct",
                    "expected": expected_str[:100],
                    "actual": user_str[:100],
                    "detail": "规则语法正确，关键元素完整",
                })
            elif match_rate >= SIMILARITY_PARTIAL:
                matched_count += 0.5
                checks.append({
                    "field": field,
                    "status": "partial",
                    "expected": expected_str[:100],
                    "actual": user_str[:100],
                    "detail": f"规则部分正确，命中 {hits}/{len(expected_values)} 个关键元素",
                })
            else:
                checks.append({
                    "field": field,
                    "status": "incorrect",
                    "expected": expected_str[:100],
                    "actual": user_str[:100],
                    "detail": f"规则缺少关键元素，期望包含: {expected_values}",
                })

        # 语法检查（正则编译）
        if "regex" in submission_text or "pattern" in submission_text:
            syntax_ok = self._check_regex_syntax(submission.get("regex_pattern", ""))
            if not syntax_ok:
                checks.append({
                    "field": "regex_pattern",
                    "status": "incorrect",
                    "expected": "有效正则表达式",
                    "actual": submission.get("regex_pattern", "")[:100],
                    "detail": "正则表达式语法错误，请检查特殊字符转义",
                })

        match_rate = matched_count / max(total_checked, 1)
        score = int(match_rate * 100 * weight)
        score = min(100, max(0, score))

        # LLM 增强：关键词匹配在灰色地带时做语义评分
        llm_adjusted = await self.llm_enhance(submission, standard, score)
        if llm_adjusted is not None:
            score = int(score * 0.6 + llm_adjusted * 0.4)
            score = min(100, max(0, score))

        analysis = self._build_analysis(checks, match_rate, required)
        suggestion = "建议检查规则语法和关键元素完整性" if score < SCORE_B else None

        return {
            "checks": checks,
            "score": score,
            "grade": "A" if score >= SCORE_A else ("B" if score >= SCORE_B else "C"),
            "status": "passed" if score >= SCORE_A else ("optimize" if score >= SCORE_B else "retry"),
            "analysis": analysis,
            "suggestion": suggestion,
            "correct_answer": correct_answer if score < SCORE_B else None,
        }

    @staticmethod
    def _check_regex_syntax(pattern: str) -> bool:
        if not pattern:
            return True
        try:
            import re
            re.compile(pattern)
            return True
        except re.error:
            return False

    def _build_analysis(self, checks: list, match_rate: float, required: list) -> str:
        incorrect = [c for c in checks if c["status"] == "incorrect"]
        partial = [c for c in checks if c["status"] == "partial"]

        lines = []
        if not incorrect and not partial:
            lines.append("规则编写正确！语法和关键元素均符合标准。")
            return "\n".join(lines)

        if incorrect:
            lines.append(f"规则存在问题（共 {len(incorrect)} 项）：")
            for c in incorrect:
                lines.append(f"  - {c['field']}：{c['detail']}")
            lines.append("")

        if partial:
            lines.append(f"规则部分完整（共 {len(partial)} 项）：")
            for c in partial:
                lines.append(f"  - {c['field']}：{c['detail']}")
            lines.append("")

        lines.append("提示：编写规则时注意转义特殊字符，使用命名捕获组提高可读性。")
        return "\n".join(lines)

    async def _build_analysis_ft(self, checks: list, match_rate: float) -> str:
        """自由文本格式的分析说明"""
        return self._build_analysis(checks, match_rate, [])


# ── 公用辅助：自由文本转字段匹配 ──

async def _free_text_check(submission: dict, key_fields: dict, correct_answer: dict, weight: float,
                           scoring_rules: dict, check_fn: callable) -> dict:
    """对自由文本格式 (user_answer) 执行全文关键词匹配，再委派给具体校验函数
    
    Returns: 已执行的各字段 checks，或 None 表示无需特殊处理（走原逻辑）
    """
    user_answer = submission.get("user_answer")
    if user_answer is None:
        return None  # 不是自由文本格式

    user_str = str(user_answer).lower().strip()
    checks = []
    matched_count = 0
    total_checked = 0
    required = scoring_rules.get("required_fields", [])
    min_match = scoring_rules.get("min_match_rate", 0.6)

    for field, expected_values in key_fields.items():
        total_checked += 1
        expected_str = str(correct_answer.get(field, "")).lower().strip()
        hits = sum(1 for kw in expected_values if kw.lower() in user_str)
        match_rate = hits / max(len(expected_values), 1)

        if match_rate >= SIMILARITY_PASS:
            matched_count += 1
            checks.append({
                "field": field, "status": "correct",
                "expected": expected_str[:100], "actual": user_str[:100],
                "detail": f"关键词 '{expected_values[0]}' 在答案中被识别",
            })
        elif match_rate >= SIMILARITY_PARTIAL:
            matched_count += 0.5
            checks.append({
                "field": field, "status": "partial",
                "expected": expected_str[:100], "actual": user_str[:100],
                "detail": f"部分匹配，命中 {hits}/{len(expected_values)} 个关键词",
            })
        else:
            checks.append({
                "field": field, "status": "incorrect",
                "expected": expected_str[:100], "actual": user_str[:80],
                "detail": f"未识别到关键词: {expected_values}",
            })

    match_rate = matched_count / max(total_checked, 1)
    score = int(match_rate * 100 * weight)
    score = min(100, max(0, score))
    required_ok = all(any(c["field"] == f and c["status"] == "correct" for c in checks) for f in required) if required else True

    grade = "A" if score >= SCORE_A else ("B" if score >= SCORE_B else "C")
    status = "passed" if (score >= SCORE_A and required_ok) else ("optimize" if score >= SCORE_B else "retry")
    analysis = check_fn(checks, match_rate)

    return {
        "checks": checks,
        "score": score,
        "grade": grade,
        "status": status,
        "analysis": analysis,
        "suggestion": f"建议补充 {'、'.join(required)} 等关键要素" if not required_ok and required else None,
        "correct_answer": correct_answer if score < SCORE_B else None,
    }


# ── 脚本类校验策略（script） ──

class ScriptCheckStrategy(BaseCheckStrategy):
    """脚本校验 — 检查配置/脚本/query的正确性"""

    strategy_type = "script"
    strategy_name = "脚本校验"

    async def check(self, submission: dict, standard: dict) -> dict:
        key_fields = standard.get("key_fields", {})
        scoring_rules = standard.get("scoring_rules", {})
        correct_answer = standard.get("correct_answer", {})
        weight = scoring_rules.get("weight", 1.0)

        # 自由文本格式快速通道
        ft_result = await _free_text_check(submission, key_fields, correct_answer, weight,
                                           scoring_rules, self._build_analysis)
        if ft_result:
            return ft_result

        checks = []
        matched_count = 0
        total_checked = 0

        for field, expected_values in key_fields.items():
            user_value = submission.get(field)
            if user_value is None:
                continue

            total_checked += 1
            user_str = str(user_value).lower().strip()
            expected_str = str(correct_answer.get(field, "")).lower().strip()

            hits = sum(1 for kw in expected_values if kw.lower() in user_str)
            match_rate = hits / max(len(expected_values), 1)

            if match_rate >= SIMILARITY_PASS:
                matched_count += 1
                checks.append({
                    "field": field,
                    "status": "correct",
                    "expected": expected_str[:100],
                    "actual": user_str[:100],
                    "detail": "脚本内容正确，关键配置完整",
                })
            elif match_rate >= SIMILARITY_PARTIAL:
                matched_count += 0.5
                checks.append({
                    "field": field,
                    "status": "partial",
                    "expected": expected_str[:100],
                    "actual": user_str[:100],
                    "detail": f"脚本部分正确，命中 {hits}/{len(expected_values)} 个关键元素",
                })
            else:
                checks.append({
                    "field": field,
                    "status": "incorrect",
                    "expected": expected_str[:100],
                    "actual": user_str[:100],
                    "detail": f"脚本缺少关键配置，期望包含: {expected_values}",
                })

        # JSON 语法检查
        if "es_query_dsl" in str(submission).lower() or "{" in str(submission):
            config_content = submission.get("es_query_dsl") or submission.get("config_content", "")
            if config_content and "{" in config_content:
                json_ok = self._check_json_syntax(config_content)
                if not json_ok:
                    checks.append({
                        "field": "config_content",
                        "status": "incorrect",
                        "expected": "有效JSON格式",
                        "actual": config_content[:100],
                        "detail": "JSON格式错误，请检查括号和引号是否匹配",
                    })

        match_rate = matched_count / max(total_checked, 1)
        score = int(match_rate * 100 * weight)
        score = min(100, max(0, score))

        # LLM 增强：关键词匹配在灰色地带时做语义评分
        llm_adjusted = await self.llm_enhance(submission, standard, score)
        if llm_adjusted is not None:
            score = int(score * 0.6 + llm_adjusted * 0.4)
            score = min(100, max(0, score))

        analysis = self._build_analysis(checks, match_rate)
        suggestion = "建议检查配置语法和参数完整性" if score < SCORE_B else None

        return {
            "checks": checks,
            "score": score,
            "grade": "A" if score >= SCORE_A else ("B" if score >= SCORE_B else "C"),
            "status": "passed" if score >= SCORE_A else ("optimize" if score >= SCORE_B else "retry"),
            "analysis": analysis,
            "suggestion": suggestion,
            "correct_answer": correct_answer if score < SCORE_B else None,
        }

    @staticmethod
    def _check_json_syntax(text: str) -> bool:
        if not text:
            return True
        try:
            import json
            json.loads(text)
            return True
        except (json.JSONDecodeError, ValueError):
            return False

    def _build_analysis(self, checks: list, match_rate: float) -> str:
        incorrect = [c for c in checks if c["status"] == "incorrect"]
        partial = [c for c in checks if c["status"] == "partial"]

        lines = []
        if not incorrect and not partial:
            lines.append("脚本编写正确！配置和参数均符合标准。")
            return "\n".join(lines)

        if incorrect:
            lines.append("脚本存在以下问题：")
            for c in incorrect:
                lines.append(f"  - {c['detail']}")
            lines.append("")

        if partial:
            lines.append("脚本部分完善：")
            for c in partial:
                lines.append(f"  - {c['detail']}")
            lines.append("")

        lines.append("提示：编写脚本时注意参数完整性，检查JSON/配置语法，注明关键参数。")
        return "\n".join(lines)


# ── 方案类校验策略（plan） ──

class PlanCheckStrategy(BaseCheckStrategy):
    """方案校验 — 检查方案/计划的合理性和完整性"""

    strategy_type = "plan"
    strategy_name = "方案校验"

    async def check(self, submission: dict, standard: dict) -> dict:
        key_fields = standard.get("key_fields", {})
        scoring_rules = standard.get("scoring_rules", {})
        correct_answer = standard.get("correct_answer", {})
        weight = scoring_rules.get("weight", 1.0)

        # 自由文本格式快速通道
        ft_result = await _free_text_check(submission, key_fields, correct_answer, weight,
                                           scoring_rules, self._build_analysis)
        if ft_result:
            return ft_result

        checks = []
        matched_count = 0
        total_checked = 0

        for field, expected_values in key_fields.items():
            user_value = submission.get(field)
            if user_value is None:
                continue

            total_checked += 1
            user_str = str(user_value).lower().strip()
            expected_str = str(correct_answer.get(field, "")).lower().strip()

            hits = sum(1 for kw in expected_values if kw.lower() in user_str)
            match_rate = hits / max(len(expected_values), 1)

            if match_rate >= SIMILARITY_PASS:
                matched_count += 1
                checks.append({
                    "field": field,
                    "status": "correct",
                    "expected": expected_str[:100],
                    "actual": user_str[:100],
                    "detail": "方案内容完整，关键要素齐全",
                })
            elif match_rate >= SIMILARITY_PARTIAL:
                matched_count += 0.5
                checks.append({
                    "field": field,
                    "status": "partial",
                    "expected": expected_str[:100],
                    "actual": user_str[:100],
                    "detail": f"方案部分完整，命中 {hits}/{len(expected_values)} 个关键要素",
                })
            else:
                checks.append({
                    "field": field,
                    "status": "incorrect",
                    "expected": expected_str[:100],
                    "actual": user_str[:100],
                    "detail": f"方案缺少关键要素，期望包含: {expected_values}",
                })

        match_rate = matched_count / max(total_checked, 1)
        score = int(match_rate * 100 * weight)
        score = min(100, max(0, score))

        # LLM 增强：关键词匹配在灰色地带时做语义评分
        llm_adjusted = await self.llm_enhance(submission, standard, score)
        if llm_adjusted is not None:
            score = int(score * 0.6 + llm_adjusted * 0.4)
            score = min(100, max(0, score))

        analysis = self._build_analysis(checks, match_rate)
        suggestion = "建议补充方案细节，确保覆盖所有关键要素" if score < SCORE_B else None

        return {
            "checks": checks,
            "score": score,
            "grade": "A" if score >= SCORE_A else ("B" if score >= SCORE_B else "C"),
            "status": "passed" if score >= SCORE_A else ("optimize" if score >= SCORE_B else "retry"),
            "analysis": analysis,
            "suggestion": suggestion,
            "correct_answer": correct_answer if score < SCORE_B else None,
        }

    def _build_analysis(self, checks: list, match_rate: float) -> str:
        incorrect = [c for c in checks if c["status"] == "incorrect"]
        partial = [c for c in checks if c["status"] == "partial"]

        lines = []
        if not incorrect and not partial:
            lines.append("方案合理完整！覆盖了所有关键要素。")
            return "\n".join(lines)

        if incorrect:
            lines.append("方案存在以下不足：")
            for c in incorrect:
                lines.append(f"  - {c['detail']}")
            lines.append("")

        if partial:
            lines.append("方案可进一步完善：")
            for c in partial:
                lines.append(f"  - {c['detail']}")
            lines.append("")

        lines.append("提示：方案类回答应包含具体步骤、技术选型理由、预期效果等要素。")
        return "\n".join(lines)