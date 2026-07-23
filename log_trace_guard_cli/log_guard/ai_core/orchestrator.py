"""AI 总调度器 — 意图识别 → 模块调用 → 结果润色，全流程编排"""
import json
import logging
import sys
import os
from typing import Optional

logger = logging.getLogger(__name__)

# ── 动态导入业务模块 ──
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(PROJECT_ROOT))

from .intent_classifier import get_classifier, IntentResult
from .rag_engine import get_rag
from .polisher import get_polisher
from .context import get_context_manager
from .llm_client import get_llm
from .prompts import build_chat_messages
from .settings import settings


class AIOrchestrator:
    """AI 总调度器
    职责链：用户输入 → 意图分类 → 上下文注入 → RAG增强 → 模块调用 → 结果润色
    """

    def __init__(self):
        self._modules = {}

    def _load_module(self, module_name: str):
        """延迟加载业务模块"""
        if module_name in self._modules:
            return self._modules[module_name]

        try:
            if module_name == "log_parse":
                from log_guard.modules.log_parse import LogParseService
                self._modules[module_name] = LogParseService()
            elif module_name == "log_collect":
                from log_guard.modules.log_collect import LogCollectService
                self._modules[module_name] = LogCollectService()
            elif module_name == "script_gen":
                from log_guard.modules.script_gen import ScriptGenService
                self._modules[module_name] = ScriptGenService()
            elif module_name == "compliance":
                from log_guard.modules.compliance import ComplianceService
                self._modules[module_name] = ComplianceService()
            elif module_name == "training":
                from log_guard.modules.training import TrainingService
                self._modules[module_name] = TrainingService()
            elif module_name == "log_correlate":
                from log_guard.modules.log_correlate import LogCorrelateService
                self._modules[module_name] = LogCorrelateService()
        except Exception as e:
            logger.warning("Failed to load module %s: %s", module_name, e)
            return None

        return self._modules.get(module_name)

    def _call_module(self, intent: IntentResult, user_input: str) -> Optional[dict]:
        """调用业务模块，返回原始结果"""
        ctx = get_context_manager().current
        module = self._load_module(intent.module)
        if module is None:
            return None

        params = intent.params or {}
        question = params.get("question", user_input)
        log_line = params.get("log_line", "")

        try:
            if intent.intent == "log_parse":
                # Case 1: 用户提供了具体日志内容 → 解析日志
                if log_line:
                    result = module.parse_log(log_line)
                    if isinstance(result, dict):
                        # 检查是否 Result 格式 (含 code/data)
                        if result.get("code") == 0 and "data" in result:
                            risk = module.assess_risk(result["data"])
                            return {"parse": result, "risk": risk}
                        # 扁平 dict 格式（直接返回）
                        return {"parse": result}
                # Case 2: 用户问的是日志分析类问题 → 识别日志类型
                if question and question != log_line:
                    result = module.identify_log_type(question)
                    return {"identify": result}
                # Case 3: 兜底
                return {"parse": module.parse_log(user_input)}

            elif intent.intent == "collection":
                from log_guard.modules.log_collect import LogCollectService
                svc = self._load_module("log_collect")
                if "诊断" in question or "故障" in question or "超时" in question or "丢包" in question:
                    return {"diagnose": svc.diagnose_fault(symptom=question)}
                if "推荐" in question or "架构" in question:
                    return {"architecture": svc.recommend_architecture(device_count=50, daily_log_volume="medium", budget="medium", team_skill="basic")}
                if "方案" in question or "采集" in question:
                    return {"plan": svc.generate_plan(device_type="server", model="generic", log_scale="medium")}
                return {"diagnose": svc.diagnose_fault(symptom=question)}

            elif intent.intent == "script_gen":
                svc = self._load_module("script_gen")
                if "正则" in question or "regex" in question.lower():
                    return {"regex": svc.generate_regex(scenario=question, log_sample=log_line or None)}
                if "ES" in question or "elastic" in question.lower() or "检索" in question:
                    return {"es_query": svc.generate_es_query(search_scenario=question)}
                if "溯源" in question or "攻击链" in question:
                    return {"trace": {"note": "请提供需要溯源的日志文件路径，或使用 --log-file 指定后重试"}}
                if "优化" in question or "纠错" in question:
                    return {"optimize": {"note": "请提供需要优化的脚本内容"}}
                return {"regex": svc.generate_regex(scenario=question)}

            elif intent.intent == "compliance":
                svc = self._load_module("compliance")
                if "基线" in question:
                    return {"baseline": svc.generate_baseline(asset_count=50, business_type="enterprise", device_types=["firewall", "server", "switch"])}
                if "自查" in question or "检查" in question:
                    return {"check": svc.compliance_check(log_retention_days=180, has_backup=True, has_tamper_proof=True, device_count=50)}
                return {"qa": svc.compliance_qa(question=question)}

            elif intent.intent == "training":
                svc = self._load_module("training")
                if "报告" in question:
                    return {"report": svc.generate_report(student_id="anonymous")}
                if "答案" in question or "提交" in question:
                    return {"note": "请使用菜单模式提交答案，或输入 '我要提交答案' 后按指引操作"}
                return {"tasks": svc.dispatch_tasks(category="basic")}

            elif intent.intent == "correlation":
                svc = self._load_module("log_correlate")
                # 检查是否提供了日志行
                log_line = params.get("log_line", "")
                if log_line:
                    lines = [log_line]
                else:
                    lines = question.split("\n") if question else [question]
                window = int(params.get("time_window", 5))
                result = svc.correlate_logs(lines, time_window_minutes=window)
                return {"correlation": result}

        except Exception as e:
            return {"error": str(e)}

        return None

    def _has_meaningful_data(self, raw_result: dict) -> bool:
        """检查业务模块返回结果是否有有效数据"""
        if not raw_result:
            return False
        # 检查是否有明确的错误标记
        if "error" in raw_result:
            return False
        # 检查各模块特有的空结果标记
        for key, val in raw_result.items():
            if isinstance(val, dict):
                # compliance qa 无匹配
                if val.get("code") == 0 and val.get("data", {}).get("matched_count", 1) == 0:
                    return False
                # 其他模块的 code != 0 表示失败
                if val.get("code", 0) != 0:
                    return False
        return True

    def process(self, user_input: str) -> dict:
        """处理用户输入：意图识别 → 执行 → 润色，完整流程"""
        ctx = get_context_manager().get_or_create()
        ctx.add_turn("user", user_input)

        # 1. 意图分类
        classifier = get_classifier()
        intent = classifier.classify(user_input)
        ctx.last_intent = intent.intent

        # 2. RAG 知识库检索
        rag = get_rag()
        rag_context = rag.search_text(user_input)

        # 3. 执行
        raw_result = None
        polisher = get_polisher()

        if intent.is_actionable:
            raw_result = self._call_module(intent, user_input)
            ctx.last_module_result = raw_result

            if raw_result and self._has_meaningful_data(raw_result):
                response = polisher.polish(
                    module=intent.intent,
                    user_input=user_input,
                    original_result=raw_result,
                    rag_context=rag_context,
                    history=ctx.get_recent_history(2),
                )
            else:
                # 业务模块无有效结果 → 走 RAG + LLM 通用问答
                response = polisher.direct_answer(
                    user_input=user_input,
                    rag_context=rag_context,
                    history=ctx.get_recent_history(2),
                )
        else:
            # 通用问答
            response = polisher.direct_answer(
                user_input=user_input,
                rag_context=rag_context,
                history=ctx.get_recent_history(2),
            )

        ctx.add_turn("assistant", response)

        return {
            "response": response,
            "intent": intent.intent,
            "confidence": intent.confidence,
            "has_rag": bool(rag_context),
            "has_module_result": raw_result is not None,
        }


_orchestrator = None


def get_orchestrator() -> AIOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AIOrchestrator()
    return _orchestrator