"""
时序推理引擎 — 为攻击链增加时间维度的推理能力

功能：
  1. 时间戳提取：从匹配行中提取时间信息
  2. 攻击阶段推断：根据关键词内容推断属于 Kill Chain 的哪个阶段
  3. 阶段序列校验：校验事件是否按预期攻击阶段顺序出现
  4. IP 因果关联：检查同一源 IP 是否在多个阶段连续出现
  5. 动态置信度调整：根据时序合理性修正置信度

集成方式：在 LogCorrelateService.correlate_logs() 中，对 AttackChainMatcher 产出的
每个 AttackChain 调用 TemporalAnalyzer.analyze() 进行时序增强。
"""

import re
from typing import Any, Dict, List, Optional, Set, Tuple

from common.logger import LogManager

logger = LogManager.get_logger()


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------

# 关键词 → 攻击阶段映射表（按 Kill Chain 顺序排列）
# 每个条目：(regex_pattern, stage_name)
# 优先级：先匹配到的获胜
KEYWORD_STAGE_RULES: List[Tuple[str, str]] = [
    # 侦查探测
    (r"scan|nmap|masscan|zmap|port.*scan|端口.*扫描|探测|侦察|recon|"
     r"dir.*bust|目录.*扫描|gobuster|路径遍历|dirsearch",
     "侦查探测"),
    # 初始入侵
    (r"password|login|auth|credential|认证|登录|brute.*force|暴力破解|爆破|"
     r"Failed\s+password|Invalid\s+user|wrong\s+credential",
     "初始入侵"),
    # 权限提升/入侵
    (r"sudo|su\b|提权|privesc|root|shadow|passwd|"
     r"shell|exec|eval\(|system\(|webshell|RCE|命令执行|远程代码|"
     r"反弹|木马|后门|phpinfo|phpmyadmin|getshell|上传|upload|whoami|"
     r"sql|injection|注入|UNION.*SELECT|1=1|SELECT.*FROM|DROP\s+TABLE",
     "权限提升/入侵"),
    # 横向移动
    (r"lateral|psexec|wmiexec|smbexec|PsExec|"
     r"横向|内网.*(扫描|探测)|ssh.*(192\.168|10\.|172\.|内网|跳转|跳板)|"
     r"SSH.*(Accepted|登录).*内网",
     "横向移动"),
    # 持久化驻留
    (r"persist|persistence|cron|scheduled|service.*(install|创建)|"
     r"backdoor|持久化|驻留|自启动|开机启动|计划任务|定时任务",
     "持久化驻留"),
    # 命令控制
    (r"callback|回连|beacon|C2|command.*control|远控|回传|"
     r"heartbeat|心跳|轮询|remote.*(connect|access)|reverse.*(shell|connect)|"
     r"受控|后门|木马",
     "命令控制"),
    # 数据窃取/破坏
    (r"exfil|exfiltration|窃取|steal|泄露|leak|"
     r"dns.*tunnel|dns隧道|outbound|出站|egress|外发|外传|"
     r"download|upload|转存|transfer|大量.*(数据|文件)|export|dump|"
     r"encrypt|加密|ransom|勒索|lock|锁定|"
     r"encrypted|README|decrypt|解密|coin|比特币|支付|赎金",
     "数据窃取/破坏"),
    # 内部威胁（特殊场景）
    (r"非工作|off.*hour|凌晨|深夜|周末|holiday|异常.*(时间|时段)|内部|insider",
     "初始入侵"),
]

# 预期的攻击阶段序列（Kill Chain 标准顺序）
STAGE_SEQUENCE = ["侦查探测", "初始入侵", "权限提升/入侵",
                  "横向移动", "持久化驻留", "命令控制", "数据窃取/破坏"]

# 时间戳提取正则模式
TIMESTAMP_PATTERNS = [
    re.compile(r"(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})"),
    re.compile(r"(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})"),
    re.compile(r"\[(\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2})"),
]

# IP 提取正则
IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")

# 时间跨度合理性范围（秒）
MIN_REASONABLE_GAP = 1        # 1秒以上才算有意义的时间间隔
MAX_REASONABLE_GAP = 1800     # 30分钟以上可能不相关


# ---------------------------------------------------------------------------
# TemporalEvent — 时序分析中的单个事件
# ---------------------------------------------------------------------------

class TemporalEvent:
    """带时间信息的攻击事件"""
    __slots__ = ("timestamp", "stage", "keyword", "src_ip", "dst_ip", "line_index", "log_line")

    def __init__(self, timestamp: Optional[str] = None, stage: str = "未知",
                 keyword: str = "", src_ip: Optional[str] = None,
                 dst_ip: Optional[str] = None, line_index: int = -1,
                 log_line: str = ""):
        self.timestamp = timestamp
        self.stage = stage
        self.keyword = keyword
        self.src_ip = src_ip
        self.dst_ip = dst_ip
        self.line_index = line_index
        self.log_line = log_line

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "stage": self.stage,
            "keyword": self.keyword[:40] if self.keyword else "",
            "src_ip": self.src_ip,
            "dst_ip": self.dst_ip,
            "line_index": self.line_index,
        }


# ---------------------------------------------------------------------------
# TemporalAnalyzer — 时序推理引擎
# ---------------------------------------------------------------------------

class TemporalAnalyzer:
    """
    时序推理引擎。

    使用方式：
        chain_dict = ...  # AttackChain.to_dict()
        enhanced = TemporalAnalyzer.analyze(chain_dict, log_lines)
        # enhanced 包含新的字段：timeline, stage_sequence_valid, temporal_score
    """

    @classmethod
    def analyze(cls, chain_dict: dict, log_lines: List[str]) -> dict:
        """
        对一条攻击链执行全量时序推理。

        Args:
            chain_dict: AttackChain.to_dict() 输出的字典
            log_lines: 原始日志行列表

        Returns:
            增强后的 chain_dict（新增 temporal_* 字段）
        """
        matched_line_indices = chain_dict.get("matched_line_indices", [])
        matched_keywords = chain_dict.get("matched_keywords", [])
        base_confidence = chain_dict.get("confidence", 0.5)

        if not matched_line_indices or not log_lines:
            chain_dict["temporal"] = {
                "enabled": False,
                "reason": "无匹配行或日志",
            }
            return chain_dict

        # 1. 提取所有匹配行的事件
        events = cls._extract_events(log_lines, matched_line_indices, matched_keywords)
        if not events:
            chain_dict["temporal"] = {"enabled": False, "reason": "无有效事件"}
            return chain_dict

        # 2. 按时间排序
        events.sort(key=lambda e: e.timestamp or "")

        # 3. 构建时间轴（含阶段标注）
        timeline = [e.to_dict() for e in events]

        # 4. 推断攻击阶段序列
        stages_observed = cls._extract_stages(events)
        stage_sequence_valid = cls._check_sequence_validity(stages_observed)

        # 5. IP 因果关联
        ip_continuity = cls._check_ip_continuity(events)

        # 6. 时间间隔评分
        time_score = cls._score_time_gaps(events)

        # 7. 动态置信度
        adjusted_confidence = cls._adjust_confidence(
            base_confidence, stage_sequence_valid, ip_continuity, time_score
        )

        # 8. 时间跨度
        time_span = cls._calc_time_span(events)

        # 写入增强字段
        chain_dict["confidence"] = round(adjusted_confidence, 2)
        chain_dict["matched_stages"] = list(stages_observed)
        chain_dict["temporal"] = {
            "enabled": True,
            "timeline": timeline,
            "event_count": len(events),
            "time_span_seconds": time_span,
            "stages_observed": list(stages_observed),
            "stage_sequence_valid": stage_sequence_valid,
            "ip_continuity_score": round(ip_continuity, 2),
            "time_gap_score": round(time_score, 2),
            "base_confidence": round(base_confidence, 2),
            "adjusted_confidence": round(adjusted_confidence, 2),
        }

        logger.info(
            f"时序增强 [{chain_dict.get('chain_name', '?')}]: "
            f"基础置信度 {base_confidence:.2f} → {adjusted_confidence:.2f}, "
            f"阶段序列 {'✓' if stage_sequence_valid else '✗'}, "
            f"IP连续性 {ip_continuity:.2f}"
        )
        return chain_dict

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    @classmethod
    def _extract_events(
        cls,
        log_lines: List[str],
        matched_indices: List[int],
        matched_keywords: List[str],
    ) -> List[TemporalEvent]:
        """从匹配行中提取事件（时间戳、IP、阶段）"""
        events: List[TemporalEvent] = []

        for idx in matched_indices:
            if idx < 0 or idx >= len(log_lines):
                continue
            line = log_lines[idx]

            # 提取时间戳
            ts = cls._extract_timestamp(line)

            # 提取 IP
            ips = IP_RE.findall(line)
            src_ip = ips[0] if ips else None
            dst_ip = ips[1] if len(ips) > 1 else None

            # 确定关键词（找到该行匹配了哪个关键字）
            matched_kw = ""
            for kw in matched_keywords:
                kw_lower = kw.lower()
                for rule_kw_part in kw_lower.split("|"):
                    rule_kw_part = rule_kw_part.strip()
                    if rule_kw_part and rule_kw_part in line.lower():
                        matched_kw = rule_kw_part
                        break
                if matched_kw:
                    break

            # 推断阶段
            stage = cls._infer_stage(matched_kw or line)

            event = TemporalEvent(
                timestamp=ts,
                stage=stage,
                keyword=matched_kw or matched_keywords[0][:40] if matched_keywords else "",
                src_ip=src_ip,
                dst_ip=dst_ip,
                line_index=idx,
                log_line=line[:120],
            )
            events.append(event)

        return events

    @classmethod
    def _extract_timestamp(cls, line: str) -> Optional[str]:
        """从日志行提取时间戳"""
        for pattern in TIMESTAMP_PATTERNS:
            m = pattern.search(line)
            if m:
                return m.group(1)
        return None

    @classmethod
    def _infer_stage(cls, text: str) -> str:
        """根据文本内容推断攻击阶段"""
        text_lower = text.lower()
        for pattern_str, stage_name in KEYWORD_STAGE_RULES:
            try:
                if re.search(pattern_str, text_lower):
                    return stage_name
            except re.error:
                continue
        return "可疑行为"

    @classmethod
    def _extract_stages(cls, events: List[TemporalEvent]) -> List[str]:
        """提取时序上出现过的攻击阶段（按首次出现顺序去重）"""
        seen: List[str] = []
        seen_set: Set[str] = set()
        for e in events:
            if e.stage and e.stage not in seen_set:
                seen.append(e.stage)
                seen_set.add(e.stage)
        return seen

    @classmethod
    def _check_sequence_validity(cls, observed: List[str]) -> bool:
        """
        校验阶段序列是否有效。

        判断逻辑：
        - 对 observed 中每一对相邻阶段 (s_i, s_j, i<j)
        - 检查它们在 STAGE_SEQUENCE 中的索引是否大致递增
        - 允许跳过阶段（如从'初始入侵'直接到'数据窃取'也算有效）
        - 不允许逆序（如'数据窃取'出现在'初始入侵'之前）
        """
        if len(observed) <= 1:
            return True  # 单阶段无法判断

        # 建立阶段名→索引的映射（不在标准序列中的阶段赋予 -1）
        seq_map = {name: i for i, name in enumerate(STAGE_SEQUENCE)}

        # 只考虑在标准序列中的阶段
        filtered = [s for s in observed if s in seq_map]
        if len(filtered) <= 1:
            return True

        # 检查是否严格非递减（允许相等或递增）
        for i in range(1, len(filtered)):
            if seq_map[filtered[i]] < seq_map[filtered[i - 1]]:
                return False

        return True

    @classmethod
    def _check_ip_continuity(cls, events: List[TemporalEvent]) -> float:
        """
        检查源 IP 是否在多个阶段连续出现。
        Returns 0.0~1.0 的连续性分数。
        """
        # 按阶段分组统计源 IP
        stage_ips: Dict[str, Set[str]] = {}
        for e in events:
            if not e.stage or not e.src_ip:
                continue
            if e.stage not in stage_ips:
                stage_ips[e.stage] = set()
            stage_ips[e.stage].add(e.src_ip)

        if len(stage_ips) <= 1:
            return 0.5  # 仅一个阶段，无法判断连续性

        # 检查相邻阶段之间是否有共同 IP
        stages_order = list(stage_ips.keys())
        common_ip_count = 0
        pair_count = 0

        for i in range(1, len(stages_order)):
            prev_stage = stages_order[i - 1]
            curr_stage = stages_order[i]
            common = stage_ips[prev_stage] & stage_ips[curr_stage]
            if common:
                common_ip_count += 1
            pair_count += 1

        if pair_count == 0:
            return 0.5

        continuity = common_ip_count / pair_count  # 0~1
        return continuity

    @classmethod
    def _score_time_gaps(cls, events: List[TemporalEvent]) -> float:
        """
        评估时间间隔的合理性。
        返回 -0.1~0.1 的评分（正值=合理，负值=不合理）。
        """
        # 只分析有明确时间戳的事件
        timed_events = [e for e in events if e.timestamp]
        if len(timed_events) < 2:
            return 0.0  # 不足以判断

        # 计算所有相邻时间间隔
        gaps = []
        for i in range(1, len(timed_events)):
            gap = cls._calc_time_diff(
                timed_events[i - 1].timestamp,
                timed_events[i].timestamp,
            )
            if gap is not None:
                gaps.append(gap)

        if not gaps:
            return 0.0

        avg_gap = sum(gaps) / len(gaps)

        # 评分逻辑
        if avg_gap < MIN_REASONABLE_GAP:
            return -0.05  # 间隔太短，可能是误报/噪声
        elif avg_gap > MAX_REASONABLE_GAP:
            return -0.10  # 间隔太长，事件可能不相关
        elif 60 <= avg_gap <= 900:  # 1~15分钟 = 理想攻击节奏
            return 0.08
        elif 10 <= avg_gap <= 3600:  # 10秒~1小时 = 合理
            return 0.04
        else:
            return -0.02  # 轻微不可信

    @classmethod
    def _calc_time_diff(cls, ts1: Optional[str], ts2: Optional[str]) -> Optional[int]:
        """计算两个时间戳的差值（秒）"""
        if not ts1 or not ts2:
            return None
        try:
            from datetime import datetime

            # 尝试多种日期格式
            formats = [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S",
                "%b %d %H:%M:%S",
                "%d/%b/%Y:%H:%M:%S",
            ]
            dt1, dt2 = None, None
            for fmt in formats:
                if dt1 is None:
                    try:
                        dt1 = datetime.strptime(ts1[:len(ts1)], fmt[:len(ts1)])
                    except ValueError:
                        pass
                if dt2 is None:
                    try:
                        dt2 = datetime.strptime(ts2[:len(ts2)], fmt[:len(ts2)])
                    except ValueError:
                        pass
            if dt1 and dt2:
                return abs(int((dt2 - dt1).total_seconds()))
        except Exception:
            pass
        return None

    @classmethod
    def _calc_time_span(cls, events: List[TemporalEvent]) -> int:
        """计算整个时间线的跨度（秒）"""
        timed_events = [e for e in events if e.timestamp]
        if len(timed_events) < 2:
            return 0
        first = timed_events[0].timestamp
        last = timed_events[-1].timestamp
        diff = cls._calc_time_diff(first, last)
        return diff or 0

    @classmethod
    def _adjust_confidence(
        cls,
        base: float,
        sequence_valid: bool,
        ip_continuity: float,
        time_score: float,
    ) -> float:
        """
        动态调整置信度。

        公式：
          adjusted = base
                     + (0.12 if sequence_valid else -0.08)
                     + ip_continuity * 0.10
                     + time_score

        结果限制在 [0.05, 0.99] 范围内。
        """
        adjusted = base

        # 阶段序列校验
        if sequence_valid:
            adjusted += 0.12
        else:
            adjusted -= 0.08

        # IP 连续性
        adjusted += ip_continuity * 0.10

        # 时间间隔合理性
        adjusted += time_score

        return max(0.05, min(0.99, adjusted))

    # ------------------------------------------------------------------
    # 实战场景生成（P2-3 Training转化）
    # ------------------------------------------------------------------

    @classmethod
    async def generate_training(cls, chain_dict: dict, log_lines: List[str]) -> dict:
        """
        从攻击链数据生成实战训练场景。

        用 LLM 根据实际攻击链数据动态生成：
          - 场景名称、描述、学习目标
          - 4个实训任务（类型识别、阶段分析、证据提取、处置建议）
          - 每个任务的标准答案要点

        Returns:
            {
                "scenario": {...},
                "tasks": [...],
                "standard_answers": {...}
            }
        """
        from core.ai_base.llm_factory import LLMFactory

        if not chain_dict or not log_lines:
            return {"scenario": None, "tasks": [], "standard_answers": {}}

        chain_name = chain_dict.get("chain_name", "unknown")
        description = chain_dict.get("description", "")
        risk_level = chain_dict.get("risk_level", "P2_低危")
        indicators = chain_dict.get("indicators", [])
        matched_keywords = chain_dict.get("matched_keywords", [])
        temporal = chain_dict.get("temporal", {})
        timeline = temporal.get("timeline", [])
        stages = temporal.get("stages_observed", [])
        sugg = chain_dict.get("suggestion", "")

        # 日志摘要（限制token量）
        log_snippet = "\n".join(log_lines[:30])
        if len(log_lines) > 30:
            log_snippet += f"\n...（共 {len(log_lines)} 行，仅展示前30行）"

        # 时间线摘要
        timeline_text = "\n".join(
            f"  {e.get('timestamp', '?')} | {e.get('stage', '?')} | {e.get('keyword', '?')[:30]} | IP={e.get('src_ip', '?')}"
            for e in (timeline or [])
        )

        prompt = f"""你是一个网络安全培训教练。基于下面真实检测到的攻击链数据，设计一套「实战溯源训练场景」。

【攻击链信息】
- 名称: {chain_name}
- 描述: {description}
- 风险等级: {risk_level}
- 发现阶段序列: {stages or '无'}
- 匹配关键词: {matched_keywords}
- 关键指标: {indicators}
- 处置建议: {sugg}

【攻击日志摘要】
{log_snippet}

【攻击时间线】
{timeline_text or '无时间数据'}

请输出以下 JSON（不要用 markdown 包裹，纯 JSON）：

{{
  "scenario": {{
    "name": "实战溯源：<攻击链中文描述>",
    "description": "<场景描述，告诉学员这是基于真实日志生成>",
    "difficulty": "中级",
    "category": "实战",
    "objectives": [
      "<学习目标1>",
      "<学习目标2>",
      "<学习目标3>"
    ]
  }},
  "tasks": [
    {{
      "task_id": "T01",
      "order": 1,
      "title": "攻击类型识别",
      "description": "<基于实际日志，让学员判断攻击类型>",
      "input_type": "log_lines",
      "submit_type": "conclusion",
      "hint": "<提示，引导学员关注关键词>"
    }},
    {{
      "task_id": "T02",
      "order": 2,
      "title": "攻击阶段分析",
      "description": "<让学员描述攻击的完整过程>",
      "input_type": "text",
      "submit_type": "conclusion",
      "hint": "<提示各阶段特征>"
    }},
    {{
      "task_id": "T03",
      "order": 3,
      "title": "关键证据提取",
      "description": "<让学员提取攻击源IP、被入侵账户等>",
      "input_type": "text",
      "submit_type": "conclusion",
      "hint": "<提示应提取哪些证据>"
    }},
    {{
      "task_id": "T04",
      "order": 4,
      "title": "处置建议",
      "description": "<让学员给出合理的安全响应方案>",
      "input_type": "text",
      "submit_type": "plan",
      "hint": "<提示从阻断、排查、恢复角度思考>"
    }}
  ],
  "standard_answers": {{
    "T01": {{
      "attack_type": "<答案>",
      "risk_level": "<答案>",
      "key_indicators": ["<关键指标>"]
    }},
    "T02": {{
      "stage_sequence": ["<阶段1>", "<阶段2>"],
      "total_stages": <数字>,
      "description": "<过程描述>"
    }},
    "T03": {{
      "src_ip": "<IP>",
      "affected_accounts": ["<账户>"],
      "timeline": "<时间范围>",
      "evidence_count": <数字>
    }},
    "T04": {{
      "immediate_actions": ["<立即措施>"],
      "investigation": ["<排查要点>"],
      "prevention": ["<预防建议>"]
    }}
  }}
}}

要求：
- 任务必须基于攻击链中的实际数据生成，不要泛泛而谈
- 标准答案要以攻击链中真实出现的信息为基准
- 难度设定为中级，适合有一定基础的学员
"""

        try:
            llm = await LLMFactory.get_light_llm()
            result = await llm.chat([
                {"role": "system", "content": "你是一个网络安全培训专家。根据真实攻击链数据生成实训场景。输出必须是纯JSON，不要用markdown包裹。"},
                {"role": "user", "content": prompt},
            ], temperature=0.3, timeout=60, max_tokens=4096)

            if not result.get("success"):
                logger.warning(f"LLM 场景生成失败: {result.get('error', '未知错误')}")
                return cls._fallback_scenario(chain_dict, log_lines)

            content = result["content"].strip()
            logger.info(f"场景 LLM 原始输出长度: {len(content)} 字符, 前80字: {content[:80]!r}")
            # 去掉 markdown 包裹
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            # 解析 JSON
            from common.json_util import JsonConfigLoader
            import json

            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                # 尝试恢复截断
                from modules.log_correlate.service import LLMChainAnalyzer
                recovered = LLMChainAnalyzer._parse_llm_json(content)
                if recovered and isinstance(recovered, list):
                    # 假设输出是数组，取第一个
                    parsed = recovered[0] if recovered else {}
                else:
                    # 尝试从纯对象恢复
                    open_brace = content.find("{")
                    close_brace = content.rfind("}")
                    if open_brace >= 0 and close_brace > open_brace:
                        try:
                            parsed = json.loads(content[open_brace:close_brace + 1])
                        except json.JSONDecodeError:
                            parsed = {}
                    else:
                        parsed = {}

            if not parsed or not parsed.get("scenario"):
                logger.warning(f"场景 LLM 输出解析失败或无 scenario 字段, parsed类型={type(parsed).__name__}, 内容前200字: {content[:200]!r}")
                return cls._fallback_scenario(chain_dict, log_lines)

            logger.info(f"实战场景生成成功: {parsed['scenario'].get('name', '?')}, {len(parsed.get('tasks', []))} 个任务")
            return {
                "scenario": parsed["scenario"],
                "tasks": parsed.get("tasks", []),
                "standard_answers": parsed.get("standard_answers", {}),
            }

        except Exception as e:
            logger.warning(f"场景生成异常: {e}")
            return cls._fallback_scenario(chain_dict, log_lines)

    @classmethod
    def _fallback_scenario(cls, chain_dict: dict, log_lines: List[str]) -> dict:
        """LLM 生成失败时的降级方案 — 基于攻击链数据构造基础场景

        标准答案直接从真实日志提取（IP/账户/时间/阶段），保证学员答对即可得分，
        而不是输出"请根据日志自行分析"之类的占位符。
        """
        chain_name = chain_dict.get("chain_name", "unknown")
        description = chain_dict.get("description", "")
        risk_level = chain_dict.get("risk_level", "P2_低危")
        indicators = chain_dict.get("indicators", [])
        sugg = chain_dict.get("suggestion", "")

        joined = "\n".join(log_lines[:100])
        # ── 从真实日志提取证据 ──
        src_ip = ""
        ip_match = re.search(r"\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b", joined)
        if ip_match:
            src_ip = ip_match.group(1)
        # 账户：优先 ssh 的 for/invalid user，其次 sudo 的 USER
        accounts: List[str] = []
        for m in re.finditer(r"(?:for|invalid user|user)\s+([A-Za-z0-9_.\-]+)", joined, re.IGNORECASE):
            acct = m.group(1)
            if acct.lower() not in ("root", "admin") and acct not in accounts:
                accounts.append(acct)
        if not accounts:
            for m in re.finditer(r"USER=(\S+)", joined):
                if m.group(1) not in accounts:
                    accounts.append(m.group(1))
        if not accounts:
            accounts = ["root"]
        # 时间范围
        timestamps = re.findall(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}", joined)
        timeline = f"{timestamps[0]} 至 {timestamps[-1]}" if len(timestamps) >= 2 else (timestamps[0] if timestamps else "")
        # 攻击类型中文名（从规则描述提炼，避免英文链名）
        attack_type = description.split("：")[0] if description and "：" in description else (description or chain_name)
        # 风险等级（从规则描述/链名推断）
        if "高危" in risk_level or "critical" in str(chain_dict.get("severity", "")).lower():
            risk_level_cn = "高危"
        elif "中危" in risk_level or "medium" in str(chain_dict.get("severity", "")).lower():
            risk_level_cn = "中危"
        elif "低危" in risk_level or "low" in str(chain_dict.get("severity", "")).lower():
            risk_level_cn = "低危"
        else:
            risk_level_cn = risk_level

        # 攻击阶段：从规则描述拆出 "A → B → C"
        stages: List[str] = []
        if description and ("→" in description or "->" in description):
            parts = re.split(r"→|->", description)
            stages = [p.strip() for p in parts if p.strip()]
        if not stages:
            stages = ["多次登录失败", "登录成功", "提权"]

        return {
            "scenario": {
                "name": f"实战溯源：{description or chain_name}",
                "description": f"基于真实检测到的攻击链「{chain_name}」生成的实战溯源训练。请分析以下{len(log_lines)}条日志，还原攻击过程并给出处置方案。",
                "difficulty": "中级",
                "category": "实战",
                "objectives": [
                    "能识别攻击链的类型和风险等级",
                    "能提取关键证据（IP、时间、账户）",
                    "能给出合理的安全处置建议",
                ],
            },
            "tasks": [
                {
                    "task_id": "T01", "order": 1,
                    "title": "攻击类型识别",
                    "description": f"分析以下{len(log_lines)}条日志，回答：(1)这是什么类型的攻击？(2)风险等级如何？",
                    "input_type": "log_lines", "submit_type": "conclusion",
                    "hint": "关注日志中的认证失败、异常请求等关键词",
                },
                {
                    "task_id": "T02", "order": 2,
                    "title": "攻击阶段分析",
                    "description": "描述攻击的完整过程，按时间顺序说明攻击者的每一步操作。",
                    "input_type": "text", "submit_type": "conclusion",
                    "hint": "关注时间戳的变化和操作的演进",
                },
                {
                    "task_id": "T03", "order": 3,
                    "title": "关键证据提取",
                    "description": "从日志中提取攻击源IP、受影响账户、攻击时间范围等关键证据。",
                    "input_type": "text", "submit_type": "conclusion",
                    "hint": "关注 from IP、for user、时间戳等字段",
                },
                {
                    "task_id": "T04", "order": 4,
                    "title": "处置建议",
                    "description": "基于检测到的攻击，给出完整的安全响应方案。",
                    "input_type": "text", "submit_type": "plan",
                    "hint": "从阻断攻击、排查影响、修复漏洞、完善监控四个角度思考",
                },
            ],
            "standard_answers": {
                "T01": {
                    "attack_type": attack_type,
                    "risk_level": risk_level_cn,
                    "key_indicators": indicators[:5] or ([src_ip] if src_ip else []),
                },
                "T02": {
                    "stage_sequence": stages,
                    "total_stages": len(stages),
                    "description": f"攻击者从 {timestamps[0] if timestamps else '? '}开始，{description or chain_name}",
                },
                "T03": {
                    "src_ip": src_ip or "待提取",
                    "affected_accounts": accounts[:5],
                    "timeline": timeline or f"{len(log_lines)} 条日志的时间范围",
                    "evidence_count": len(log_lines),
                },
                "T04": {
                    "immediate_actions": ["封禁攻击源IP", "隔离受影响系统"],
                    "investigation": ["检查受影响账户的活动记录", "排查是否有横向移动"],
                    "prevention": [sugg or "加强访问控制并监控异常行为"],
                },
            },
        }
