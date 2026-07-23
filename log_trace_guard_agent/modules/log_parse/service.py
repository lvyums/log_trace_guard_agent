"""模块一业务逻辑编排 — 规则引擎 + RAG + LLM 三层编排"""

import json
import re
from typing import Optional

from modules.log_parse.parser_factory import LogParserFactory
from core.ai_base.llm_factory import LLMFactory
from core.ai_base.prompt_manager import PromptManager
from core.ai_base.rag_factory import RAGFactory
from core.context_manager import ContextManager, ModuleContext
from core.rule_engine.regex_rule import RegexRuleEngine
from core.rule_engine.risk_baseline import RiskBaseline
from app.schemas.context_schema import ModuleStatus
from app.settings import settings, RiskLevel
from common.json_util import JsonConfigLoader
from common.logger import LogManager
from common.result_util import Result
from common.str_util import clean_syslog_prefix, is_gibberish, normalize_whitespace

logger = LogManager.get_logger()


class LogParseService:
    """日志解析模块 — 业务逻辑编排"""

    # ── 公开方法 ──

    @staticmethod
    async def identify_log_type(log_line: str, context: ContextManager) -> Result:
        """识别日志类型 — 多特征加权识别 + LLM 降级"""
        # 0. 预处理
        cleaned = LogParseService._preprocess(log_line)
        if not cleaned:
            return Result.fail("日志内容为空或无效")

        # 1. 规则引擎匹配
        rule_match = RegexRuleEngine.match(cleaned)
        device_type = "unknown"
        confidence = 0.0
        identify_reason = ""

        if rule_match:
            device_type = rule_match.rule.device_type
            priority_weight = min(rule_match.rule.priority / 10, 1.0)
            confidence = 60 + priority_weight * 30  # 60-90
            identify_reason = f"规则引擎命中: {rule_match.rule.name}"
        else:
            # 2. 多特征加权识别
            features = LogParseService._extract_features(cleaned)
            if features:
                device_type, confidence, identify_reason = features

        # 3. RAG 检索补充
        rag_context = ""
        try:
            kb = RAGFactory.get_kb("log_basics")
            rag_result = kb.retrieve(cleaned, top_k=3)
            if rag_result.items:
                rag_context = rag_result.items[0].get("document", "")
                if not identify_reason:
                    identify_reason = "RAG知识库匹配"
        except Exception as e:
            logger.warning(f"RAG 检索失败: {e}")

        # 4. LLM 降级：当规则引擎和特征匹配都失败时
        if device_type == "unknown" or confidence < 30:
            llm_result = await LogParseService._llm_identify_fallback(cleaned)
            if llm_result:
                device_type = llm_result.get("device_type", device_type)
                llm_confidence = llm_result.get("confidence", 0)
                if llm_confidence > confidence:
                    confidence = llm_confidence
                    identify_reason = llm_result.get("identify_reason", "LLM降级识别")
                    if identify_reason:
                        identify_reason = f"LLM降级: {identify_reason[:100]}"

        if not identify_reason:
            identify_reason = "未能识别日志类型，特征不明确"

        # 5. 更新上下文
        ctx = ModuleContext(
            module_id="log_parse",
            status=ModuleStatus.SUCCESS if device_type != "unknown" else ModuleStatus.WARNING,
            input={"log_line": cleaned},
            output={"device_type": device_type, "confidence": confidence, "reason": identify_reason},
        )
        context.set_module_result("log_parse", ctx)

        return Result.ok({
            "device_type": device_type,
            "confidence": round(confidence, 1),
            "identify_reason": identify_reason,
        })

    @staticmethod
    async def parse_log(log_line: str, context: ContextManager) -> Result:
        """全流程解析：预处理 → 识别 → 提取字段 → 结构校验（含 LLM 降级）"""
        # 0. 在预处理前提取时间戳（syslog前缀会被清洗掉）
        from common.time_util import parse_log_time
        original_timestamp = parse_log_time(log_line)

        # 1. 预处理
        cleaned = LogParseService._preprocess(log_line)
        if not cleaned:
            LogManager.log_parse_failure(log_line, "日志内容为空")
            return Result.fail("日志内容为空或无效")

        # 2. 解析日志
        parsed = LogParserFactory.parse(cleaned)
        if parsed is None:
            # 兜底1: LLM 降级解析
            llm_parsed = await LogParseService._llm_parse_fallback(cleaned)
            if llm_parsed:
                parsed = llm_parsed
                logger.info("LLM 降级解析成功")
            else:
                # 兜底2: 返回通用解析结果 + 人工复核提示
                fallback = {
                    "timestamp": original_timestamp,
                    "src_ip": None,
                    "dst_ip": None,
                    "user": None,
                    "status": None,
                    "device_type": "unknown",
                    "raw_log": cleaned[:500],
                    "missing_fields": ["timestamp", "src_ip", "user", "status"],
                    "fallback_note": "无法识别日志格式，已返回通用解析结果，建议人工复核",
                }
                LogManager.log_parse_failure(log_line, "无法识别日志格式，使用兜底解析")
                return Result.ok(fallback)

        # 3. 使用预处理前提取的时间戳（如果解析器没有找到时间戳）
        if not parsed.get("timestamp") and original_timestamp:
            parsed["timestamp"] = original_timestamp

        # 3. 标记缺失字段
        missing = []
        required = ["timestamp", "src_ip", "user", "status"]
        for f in required:
            if not parsed.get(f):
                parsed[f"{f}_missing"] = True
                missing.append(f)

        parsed["missing_fields"] = missing

        # 4. 更新上下文
        ctx = ModuleContext(
            module_id="log_parse",
            status=ModuleStatus.SUCCESS if len(missing) < 3 else ModuleStatus.PARTIAL,
            input={"log_line": cleaned},
            output=parsed,
        )
        context.set_module_result("log_parse", ctx)

        return Result.ok(parsed)

    @staticmethod
    async def assess_risk(parsed_fields: dict, context: ContextManager,
                          device_type: Optional[str] = None) -> Result:
        """行为研判：风险基线匹配 + 多特征综合评分"""
        # 如果有传入 device_type，注入到 parsed_fields 中
        if device_type and parsed_fields.get("device_type") in (None, "unknown"):
            parsed_fields["device_type"] = device_type

        # 使用风险基线进行评估
        matches = RiskBaseline.evaluate(parsed_fields)

        if not matches:
            return Result.ok({
                "risk_level": RiskLevel.P3_NOISE.value,
                "confidence": 0.0,
                "attack_type": None,
                "risk_desc": "未命中任何风险规则，行为正常",
                "match_rule_ids": [],
                "suggestion": None,
            })

        # 取最高风险等级的结果
        top = matches[0]
        rule_ids = [m.rule_id for m in matches]

        # 综合置信度 = 最高命中置信度
        combined_confidence = max(m.confidence for m in matches)

        return Result.ok({
            "risk_level": top.risk_level,
            "confidence": round(combined_confidence, 1),
            "attack_type": top.attack_type,
            "risk_desc": top.risk_desc,
            "match_rule_ids": rule_ids,
            "suggestion": top.suggestion,
        })

    @staticmethod
    async def batch_parse(logs: list[str], do_assess: bool = False,
                          context: Optional[ContextManager] = None) -> Result:
        """批量解析：多条日志一次性识别、解析、可选风险研判"""
        items = []
        risk_counts = {RiskLevel.P0_HIGH: 0, RiskLevel.P1_MEDIUM: 0,
                       RiskLevel.P2_LOW: 0, RiskLevel.P3_NOISE: 0}

        for i, log_line in enumerate(logs):
            item = {
                "index": i, "log_line": log_line[:100],
                "parse_result": None, "risk_result": None, "error": None,
            }

            # 解析
            parse_result = await LogParseService.parse_log(
                log_line, context or ContextManager.create("")
            )
            if not parse_result["code"] == 0:
                item["error"] = parse_result["msg"]
                items.append(item)
                continue

            item["parse_result"] = parse_result["data"]

            # 可选风险研判
            if do_assess:
                risk = await LogParseService.assess_risk(
                    parse_result["data"],
                    context or ContextManager.create(""),
                )
                if risk["code"] == 0:
                    item["risk_result"] = risk["data"]
                    risk_level_val = risk["data"].get("risk_level", "")
                    for level in RiskLevel:
                        if level.value == risk_level_val:
                            risk_counts[level] += 1
                            break
                else:
                    item["risk_result"] = None

            items.append(item)

        success_count = sum(1 for i in items if i["error"] is None)
        fail_count = len(items) - success_count

        risk_summary = None
        if do_assess:
            risk_summary = {level.value: count for level, count in risk_counts.items()}

        return Result.ok({
            "total": len(logs),
            "success_count": success_count,
            "fail_count": fail_count,
            "items": items,
            "risk_summary": risk_summary,
        })

    @staticmethod
    async def explain_field(field_name: str,
                            device_type: Optional[str] = None,
                            context: Optional[ContextManager] = None) -> Result:
        """字段释义：RAG 检索 + 设备类型上下文"""
        query = f"字段解释 {field_name}"
        if device_type:
            query = f"[{device_type}] {query}"

        rag_content = ""
        try:
            kb = RAGFactory.get_kb("log_basics")
            rag_result = kb.retrieve(query, top_k=3)
            if rag_result.items:
                rag_content = "\n".join(
                    [item.get("document", "") for item in rag_result.items]
                )
        except Exception as e:
            logger.warning(f"RAG 检索失败: {e}")

        explanation = f"字段: {field_name}"
        if device_type:
            explanation += f"\n\n日志类型: {device_type}"
        if rag_content:
            explanation += f"\n\n专业定义: {rag_content[:300]}"
        else:
            explanation += "\n\n暂无知识库匹配内容，请参考通用文档。"

        return Result.ok({
            "field": field_name,
            "explanation": explanation,
            "device_type": device_type,
        })

    @staticmethod
    async def explain_fields_batch(field_names: list[str],
                                   device_type: Optional[str] = None,
                                   context: Optional[ContextManager] = None) -> Result:
        """批量字段释义"""
        results = []
        for field_name in field_names:
            result = await LogParseService.explain_field(
                field_name, device_type, context
            )
            if result["code"] == 0:
                results.append(result["data"])
        return Result.ok({"fields": results, "device_type": device_type})

    # ── LLM 降级方法 ──

    @staticmethod
    async def _llm_identify_fallback(log_line: str) -> Optional[dict]:
        """LLM 降级识别日志类型"""
        if not settings.llm_api_key:
            return None

        try:
            prompt = PromptManager.get_prompt(
                "log_identify_fallback", log_line=log_line[:1500]
            )
            llm = await LLMFactory.get_main_llm()
            result = await llm.chat([
                {"role": "system", "content": "你是一个日志分析专家。只返回JSON，不要包含其他文字。"},
                {"role": "user", "content": prompt},
            ])

            if result.get("success"):
                content = result["content"]
                # 从 markdown 代码块或纯 JSON 中提取
                json_str = LogParseService._extract_json(content)
                if json_str:
                    parsed = json.loads(json_str)
                    if isinstance(parsed, dict):
                        return parsed
        except Exception as e:
            logger.warning(f"LLM 降级识别失败: {e}")
        return None

    @staticmethod
    async def _llm_parse_fallback(log_line: str) -> Optional[dict]:
        """LLM 降级解析日志为结构化字段"""
        if not settings.llm_api_key:
            return None

        try:
            prompt = PromptManager.get_prompt(
                "log_parse_fallback", log_line=log_line[:2000]
            )
            llm = await LLMFactory.get_main_llm()
            result = await llm.chat([
                {"role": "system", "content": "你是一个日志解析专家。只返回JSON，不要包含其他文字。"},
                {"role": "user", "content": prompt},
            ])

            if result.get("success"):
                content = result["content"]
                json_str = LogParseService._extract_json(content)
                if json_str:
                    parsed = json.loads(json_str)
                    if isinstance(parsed, dict):
                        return parsed
        except Exception as e:
            logger.warning(f"LLM 降级解析失败: {e}")
        return None

    @staticmethod
    def _extract_json(text: str) -> Optional[str]:
        """从 LLM 输出中提取 JSON 字符串

        支持纯 JSON、markdown 代码块（```json ... ```）、
        或被其他文字包裹的 JSON 对象。
        """
        if not text:
            return None

        # 尝试从 ```json ``` 代码块提取
        json_block = re.search(
            r'```(?:json)?\s*\n?(\{.*?\})\n?\s*```', text, re.DOTALL
        )
        if json_block:
            return json_block.group(1).strip()

        # 尝试从 ``` 代码块提取
        block = re.search(r'```\s*\n?(\{.*?\})\n?\s*```', text, re.DOTALL)
        if block:
            return block.group(1).strip()

        # 尝试找到最外层的 { }
        brace_start = text.find('{')
        brace_end = text.rfind('}')
        if brace_start != -1 and brace_end > brace_start:
            candidate = text[brace_start:brace_end + 1]
            try:
                json.loads(candidate)
                return candidate
            except json.JSONDecodeError:
                pass

        return None

    # ── 私有辅助方法 ──

    @staticmethod
    def _preprocess(log_line: str) -> str:
        """预处理日志：清洗 + 校验"""
        if not log_line or not log_line.strip():
            return ""
        cleaned = clean_syslog_prefix(log_line.strip())
        cleaned = normalize_whitespace(cleaned)
        if is_gibberish(cleaned):
            return ""
        return cleaned

    @staticmethod
    def _extract_features(log_line: str) -> Optional[tuple]:
        """多特征加权识别日志类型（配置驱动）

        特征数据从 data/rule_data/log_features.json 加载，
        外部修改 JSON 即可调整特征规则，无需改代码。
        """
        config_path = f"{settings.rule_data_dir}/log_features.json"
        features = JsonConfigLoader.load(config_path)
        if not features:
            return None

        log_lower = log_line.lower()

        best_type = "unknown"
        best_score = 0.0
        best_reason = ""

        for dtype, feats in features.items():
            score = 0.0
            matched = []
            for feat in feats:
                keyword = feat["keyword"]
                weight = feat["weight"]
                if keyword in log_lower:
                    score += weight
                    matched.append(keyword)

            if score > best_score:
                best_score = score
                best_type = dtype
                best_reason = f"多特征匹配: {', '.join(matched[:3])}"

        if best_score < 0.5:
            return None

        # 置信度映射
        confidence = min(best_score * 100, 95)
        return (best_type, confidence, best_reason)