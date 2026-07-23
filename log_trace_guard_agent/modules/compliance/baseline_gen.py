"""模块二：合规基线生成 + 合规自查策略 — 基于外部配置"""

from typing import Optional

from modules.compliance.compliance_rule import BaseComplianceStrategy
from common.logger import LogManager
from common.json_util import JsonConfigLoader

logger = LogManager.get_logger()


# ── 合规基线自动生成策略 ──

class BaselineGenStrategy(BaseComplianceStrategy):
    """个性化合规基线自动生成 — 基于外部配置的基线模板"""

    strategy_type = "baseline_gen"
    strategy_name = "合规基线生成"

    def __init__(self):
        self._baselines = None

    def _load_baselines(self) -> list[dict]:
        """从外部配置加载基线模板"""
        if self._baselines is None:
            from app.settings import settings
            path = f"{settings.rule_data_dir}/compliance_baselines.json"
            self._baselines = JsonConfigLoader.load(path) or []
        return self._baselines

    def execute(self, params: dict) -> dict:
        """执行基线生成"""
        asset_count = params.get("asset_count", 10)
        business_type = params.get("business_type", "enterprise")
        device_types = params.get("device_types", [])
        monitor_scenarios = params.get("monitor_scenarios")
        industry = params.get("industry")

        all_baselines = self._load_baselines()
        logger.info(f"基线生成: 设备类型={device_types}, 监控场景={monitor_scenarios}, 总基线数={len(all_baselines)}")
        selected = []

        # 按设备类型筛选基线
        if device_types:
            for bl in all_baselines:
                bl_devices = [d.lower() for d in bl.get("applicable_devices", [])]
                if "all" in bl_devices:
                    selected.append(bl)
                elif any(d.lower() in bl_devices for d in device_types):
                    selected.append(bl)
        else:
            selected = list(all_baselines)

        logger.info(f"设备类型筛选后: {len(selected)} 条基线")

        # 按监控场景筛选（支持模糊匹配）
        if monitor_scenarios:
            scenario_keywords = [s.lower() for s in monitor_scenarios]
            # 场景关键词映射：用户输入 -> 基线 monitor_scenario 子串
            scenario_map = {
                "入侵": ["异常登录", "端口扫描", "高危命令", "异常外联"],
                "登录": ["异常登录", "异地ip"],
                "扫描": ["端口扫描"],
                "数据库": ["数据库批量"],
                "数据泄露": ["数据库批量", "异常外联"],
                "恶意软件": ["高危命令", "异常外联"],
                "外联": ["异常外联"],
                "日志": ["日志存储"],
                "命令": ["高危命令"],
            }
            # 展开关键词
            expanded_keywords = set()
            for kw in scenario_keywords:
                expanded_keywords.add(kw)
                for map_key, map_values in scenario_map.items():
                    if map_key in kw:
                        expanded_keywords.update(map_values)

            logger.info(f"监控场景关键词(展开后): {expanded_keywords}")
            for bl in selected:
                ms = bl.get("monitor_scenario", "").lower()
                matches = [kw for kw in expanded_keywords if kw in ms]
                logger.info(f"  基线 '{bl.get('name')}' monitor_scenario='{ms}' 匹配: {matches}")
            selected = [
                bl for bl in selected
                if any(kw in bl.get("monitor_scenario", "").lower() for kw in expanded_keywords)
            ]

        logger.info(f"监控场景筛选后: {len(selected)} 条基线")

        # 按资产规模调整基线参数
        adjusted = self._adjust_by_scale(selected, asset_count, business_type, industry)

        # 构建输出
        baselines_out = []
        for bl in adjusted:
            thresholds_out = []
            for name, desc in bl.get("thresholds", {}).items():
                thresholds_out.append({
                    "name": name,
                    "description": desc,
                    "severity": bl.get("severity", "medium"),
                })

            baselines_out.append({
                "baseline_id": bl.get("baseline_id", ""),
                "name": bl.get("name", ""),
                "category": bl.get("category", ""),
                "description": bl.get("description", ""),
                "monitor_scenario": bl.get("monitor_scenario", ""),
                "thresholds": thresholds_out,
                "check_frequency": bl.get("check_frequency", ""),
                "alert_standard": bl.get("alert_standard", ""),
                "applicable_devices": bl.get("applicable_devices", []),
                "severity": bl.get("severity", "medium"),
                "remediation": bl.get("remediation", ""),
            })

        summary = self._build_summary(baselines_out, asset_count, business_type)

        return {
            "baselines": baselines_out,
            "summary": summary,
            "note": self._build_note(asset_count, industry, selected),
        }

    def _adjust_by_scale(self, baselines: list[dict], asset_count: int,
                         business_type: str, industry: Optional[str] = None) -> list[dict]:
        """根据资产规模和业务类型调整基线"""
        adjusted = []
        for bl in baselines:
            bl_copy = dict(bl)
            thresholds = dict(bl.get("thresholds", {}))

            # 小规模资产（<30台），调松告警阈值
            if asset_count < 30:
                for key in list(thresholds.keys()):
                    if "数量" in thresholds.get(key, "") or "超过" in thresholds.get(key, ""):
                        if "10000" in thresholds[key]:
                            thresholds[key] = thresholds[key].replace("10000", "5000")
                        if "100MB" in thresholds[key]:
                            thresholds[key] = thresholds[key].replace("100MB", "50MB")
                        if "500MB" in thresholds[key]:
                            thresholds[key] = thresholds[key].replace("500MB", "200MB")

            # 大规模资产（>500台），调紧告警阈值
            elif asset_count > 500:
                for key in list(thresholds.keys()):
                    if "5分钟" in thresholds.get(key, ""):
                        thresholds[key] = thresholds[key].replace("5分钟", "3分钟")
                    if "1小时" in thresholds.get(key, ""):
                        thresholds[key] = thresholds[key].replace("1小时", "30分钟")

            # 金融行业特殊处理
            if industry and "金融" in industry:
                for key in list(thresholds.keys()):
                    if "5分钟" in thresholds.get(key, ""):
                        thresholds[key] = thresholds[key].replace("5分钟", "2分钟")
                    if "1小时" in thresholds.get(key, ""):
                        thresholds[key] = thresholds[key].replace("1小时", "15分钟")

            # 教育行业宽松处理
            if industry and ("教育" in industry or "园区" in industry):
                bl_copy["check_frequency"] = bl.get("check_frequency", "").replace(
                    "实时", "每5分钟"
                ) if "实时" in bl.get("check_frequency", "") else bl.get("check_frequency", "")

            bl_copy["thresholds"] = thresholds
            adjusted.append(bl_copy)

        return adjusted

    def _build_summary(self, baselines: list, asset_count: int, business_type: str) -> str:
        """构建基线总结"""
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        by_severity = {}
        for bl in baselines:
            sev = bl.get("severity", "medium")
            by_severity.setdefault(sev, []).append(bl["name"])

        biz_labels = {
            "enterprise": "企业", "gov": "政府", "education": "教育",
            "finance": "金融", "medical": "医疗",
        }
        biz_label = biz_labels.get(business_type, business_type)

        summary = (
            f"根据您的资产规模（{asset_count}台设备）和业务类型（{biz_label}），"
            f"为您生成了 {len(baselines)} 条监控基线。\n\n"
        )

        if "critical" in by_severity:
            summary += f"🛑 严重级别基线：{len(by_severity['critical'])} 条\n"
        if "high" in by_severity:
            summary += f"🔴 高级别基线：{len(by_severity['high'])} 条\n"
        if "medium" in by_severity:
            summary += f"🟡 中级别基线：{len(by_severity['medium'])} 条\n"
        if "low" in by_severity:
            summary += f"🟢 低级别基线：{len(by_severity['low'])} 条\n"

        summary += (
            f"\n建议按严重级别优先级逐步实施，先部署严重/高级别基线，"
            f"再逐步完善中低级别基线。"
        )
        return summary

    def _build_note(self, asset_count: int, industry: Optional[str] = None,
                    selected: list = None) -> str:
        """生成补充说明"""
        notes = []
        if asset_count < 30:
            notes.append("小规模资产（<30台），已适当调松告警阈值，减少误报")
        if asset_count > 500:
            notes.append("大规模资产（>500台），已适当调紧告警阈值，提升检测灵敏度")
        if industry and ("金融" in industry):
            notes.append("金融行业，已启用更严格的监控频率和阈值")
        if industry and ("教育" in industry or "园区" in industry):
            notes.append("教育/园区场景，已调整为适合教育网的监控频率")
        if not notes:
            notes.append("基线已按默认配置生成，可根据实际运行情况调整阈值")
        return "；".join(notes)


# ── 合规自查与缺口整改策略 ──

class ComplianceCheckStrategy(BaseComplianceStrategy):
    """合规自查与缺口整改 — 对比现状与标准，输出缺口清单"""

    strategy_type = "check"
    strategy_name = "合规自查"

    def __init__(self):
        self._standards = None

    def _load_standards(self) -> list[dict]:
        """从外部配置加载合规标准"""
        if self._standards is None:
            from app.settings import settings
            path = f"{settings.rule_data_dir}/compliance_standards.json"
            self._standards = JsonConfigLoader.load(path) or []
        return self._standards

    def execute(self, params: dict) -> dict:
        """执行合规自查"""
        # 提取用户当前状态
        log_retention = params.get("log_retention_days")
        has_backup = params.get("has_backup")
        has_tamper_proof = params.get("has_tamper_proof")
        backup_frequency = params.get("backup_frequency", "")
        device_count = params.get("device_count", 0)
        has_audit = params.get("has_audit_mechanism")
        has_ntp = params.get("has_ntp")
        audit_frequency = params.get("audit_frequency", "")
        has_alert = params.get("has_alert_system")
        has_bastion = params.get("has_bastion")

        standards = self._load_standards()
        gaps = []

        # 检查每个标准条目
        for std in standards:
            for item in std.get("items", []):
                gap = self._check_item(item, {
                    "log_retention_days": log_retention,
                    "has_backup": has_backup,
                    "has_tamper_proof": has_tamper_proof,
                    "backup_frequency": backup_frequency,
                    "has_audit": has_audit,
                    "has_ntp": has_ntp,
                    "audit_frequency": audit_frequency,
                    "has_alert": has_alert,
                    "has_bastion": has_bastion,
                    "device_count": device_count,
                })
                if gap:
                    gaps.append(gap)

        # 去重：相同 requirement 的缺口只保留风险最高的
        gaps = self._deduplicate_gaps(gaps)

        # 计算合规评分
        total = len(gaps)
        critical = sum(1 for g in gaps if g["risk_level"] == "critical")
        high = sum(1 for g in gaps if g["risk_level"] == "high")
        medium = sum(1 for g in gaps if g["risk_level"] == "medium")
        low = sum(1 for g in gaps if g["risk_level"] == "low")

        # 评分算法：满分100，严重扣30，高扣15，中扣8，低扣3
        score = max(0, 100 - (critical * 30 + high * 15 + medium * 8 + low * 3))

        summary = self._build_summary(gaps, critical, high, medium, low, score)

        return {
            "gaps": gaps,
            "summary": summary,
            "overall_score": score,
            "critical_count": critical,
            "medium_count": medium,
            "low_count": low,
            "note": "自查结果基于您提供的信息，建议结合实际情况进行现场复核",
        }

    def _check_item(self, item: dict, status: dict) -> dict:
        """检查单条合规标准是否满足"""
        item_id = item.get("item_id", "")
        requirement = item.get("requirement", "")
        detail = item.get("detail", "")
        risk_if_not = item.get("risk_if_not", "")
        check_method = item.get("check_method", "")

        gap = None

        # 检查日志留存（GB-001, CSL-001）
        if item_id in ("GB-001", "CSL-001"):
            retention = status.get("log_retention_days")
            if retention is not None and retention < 180:
                gap = self._make_gap(
                    item_id, requirement, detail, risk_if_not,
                    f"当前日志留存 {retention} 天，不足180天（6个月）",
                    "high",
                    [
                        "扩展日志存储容量（如增加磁盘或配置日志归档）",
                        "配置日志轮转策略，确保6个月数据可查",
                        "启用日志压缩，降低存储成本",
                        f"建议扩容至当前容量的 {max(2, 180 // max(retention, 1))} 倍以上",
                    ],
                )
            elif retention is None:
                gap = self._make_gap(
                    item_id, requirement, detail, risk_if_not,
                    "未提供日志留存时长信息，无法确认合规",
                    "medium",
                    ["检查当前日志存储策略，确认留存天数", "配置日志轮转和归档策略"],
                )

        # 检查防篡改（GB-003）
        elif item_id == "GB-003":
            if status.get("has_tamper_proof") is False:
                gap = self._make_gap(
                    item_id, requirement, detail, risk_if_not,
                    "当前未启用日志防篡改机制",
                    "high",
                    [
                        "启用日志防篡改功能（如WORM存储、区块链存证、日志签名）",
                        "配置日志文件的权限控制，仅允许审计员访问",
                        "部署日志完整性校验工具（如Tripwire、AIDE）",
                    ],
                )

        # 检查备份（GB-004）
        elif item_id == "GB-004":
            if status.get("has_backup") is False:
                gap = self._make_gap(
                    item_id, requirement, detail, risk_if_not,
                    "当前未配置日志备份",
                    "high",
                    [
                        "配置日志定期备份策略（推荐每天增量备份，每周全量备份）",
                        "设置异地备份存储（如远程NAS、对象存储）",
                        "定期验证备份数据的可恢复性（每月至少1次）",
                    ],
                )
            elif status.get("has_backup") is True and status.get("backup_frequency"):
                freq = status["backup_frequency"].lower()
                if "月" not in freq and "周" not in freq and "天" not in freq:
                    gap = self._make_gap(
                        item_id, requirement, detail, risk_if_not,
                        f"备份频率（{status['backup_frequency']}）不明确，建议至少每月1次",
                        "medium",
                        ["确认备份周期，建议不超过1个月", "检查异地备份策略是否已配置"],
                    )

        # 检查审计记录保护（GB-005）
        elif item_id == "GB-005":
            if status.get("has_audit") is False:
                gap = self._make_gap(
                    item_id, requirement, detail, risk_if_not,
                    "当前未配置审计机制",
                    "high",
                    [
                        "建立日志审计制度，明确审计频率和责任人",
                        "部署日志审计系统（如SIEM、日志分析平台）",
                        "配置审计记录的访问控制，防止未授权访问",
                        "建议每季度至少执行1次全面审计",
                    ],
                )

        # 检查时钟同步（GB-006）
        elif item_id == "GB-006":
            if status.get("has_ntp") is False:
                gap = self._make_gap(
                    item_id, requirement, detail, risk_if_not,
                    "当前未启用NTP时钟同步",
                    "medium",
                    [
                        "配置NTP服务器（推荐使用国家授时中心或内网NTP服务器）",
                        "在所有网络设备、安全设备、服务器上启用NTP同步",
                        "定期检查设备时间偏差，确保偏差不超过5秒",
                    ],
                )

        # 检查实时告警（GB-007）
        elif item_id == "GB-007":
            if status.get("has_alert") is False:
                gap = self._make_gap(
                    item_id, requirement, detail, risk_if_not,
                    "当前未配置实时告警系统",
                    "high",
                    [
                        "部署安全告警系统（如SIEM、SOC平台）",
                        "配置告警规则，覆盖异常登录、端口扫描、高危命令等场景",
                        "设置告警通知渠道（邮件、短信、即时通讯）",
                        "建立告警处置流程，明确响应时间和责任人",
                    ],
                )

        # 检查用户行为审计（GB-008）
        elif item_id == "GB-008":
            if status.get("has_bastion") is False:
                gap = self._make_gap(
                    item_id, requirement, detail, risk_if_not,
                    "当前未部署堡垒机，无法审计用户操作行为",
                    "medium",
                    [
                        "部署堡垒机（如JumpServer、齐治、安恒）",
                        "配置账号管理和权限控制",
                        "启用操作审计和录像回放功能",
                    ],
                )

        # 检查数据操作日志（DSL-001）
        elif item_id == "DSL-001":
            if status.get("has_audit") is False:
                gap = self._make_gap(
                    item_id, requirement, detail, risk_if_not,
                    "当前未配置数据库审计机制",
                    "high",
                    [
                        "启用数据库审计日志（如MySQL General Log、Audit Plugin）",
                        "配置数据库操作记录范围（SELECT/INSERT/UPDATE/DELETE/DDL）",
                        "确保审计日志存储安全，防止篡改",
                    ],
                )

        return gap

    def _make_gap(self, item_id: str, requirement: str, detail: str,
                  risk_if_not: str, current_status: str, risk_level: str,
                  remediation_steps: list[str]) -> dict:
        """创建合规缺口对象"""
        priority_map = {
            "critical": "P0-立即修复",
            "high": "P1-尽快修复",
            "medium": "P2-计划修复",
            "low": "P3-持续改进",
        }

        # 根据 risk_level 字段内容确定标准引用
        if "等保" in detail or "GB" in item_id:
            standard_ref = "等保2.0"
        elif "网安法" in detail or "CSL" in item_id:
            standard_ref = "网络安全法"
        elif "数据安全法" in detail or "DSL" in item_id:
            standard_ref = "数据安全法"
        else:
            standard_ref = "通用合规要求"

        return {
            "gap_id": item_id,
            "standard_ref": standard_ref,
            "requirement": requirement,
            "current_status": current_status,
            "risk_level": risk_level,
            "risk_description": risk_if_not,
            "remediation_steps": remediation_steps,
            "priority": priority_map.get(risk_level, "P2-计划修复"),
        }

    def _deduplicate_gaps(self, gaps: list) -> list:
        """去重：相同 requirement 的缺口只保留风险最高的，并合并标准来源"""
        if not gaps:
            return gaps

        risk_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        seen = {}  # requirement -> index in deduped list

        deduped = []
        for gap in gaps:
            req = gap.get("requirement", "")
            if req in seen:
                # 合并标准来源
                idx = seen[req]
                existing_ref = deduped[idx].get("standard_ref", "")
                new_ref = gap.get("standard_ref", "")
                if new_ref not in existing_ref:
                    deduped[idx]["standard_ref"] = f"{existing_ref} / {new_ref}"
                # 保留风险更高的
                if risk_order.get(gap.get("risk_level"), 9) < risk_order.get(deduped[idx].get("risk_level"), 9):
                    deduped[idx]["risk_level"] = gap["risk_level"]
                    deduped[idx]["priority"] = gap.get("priority", deduped[idx].get("priority"))
            else:
                seen[req] = len(deduped)
                deduped.append(gap)

        return deduped

    def _build_summary(self, gaps: list, critical: int, high: int,
                       medium: int, low: int, score: int) -> str:
        """构建自查总结"""
        if not gaps:
            return "未发现合规缺口，当前日志管理状态良好，继续保持。"

        total = len(gaps)
        summary = (
            f"合规自查发现 {total} 个合规缺口。\n\n"
        )

        if critical > 0:
            summary += f"🛑 严重缺口：{critical} 个 — 立即整改，涉及核心合规项\n"
        if high > 0:
            summary += f"🔴 高风险缺口：{high} 个 — 尽快整改，存在合规风险\n"
        if medium > 0:
            summary += f"🟡 中风险缺口：{medium} 个 — 计划整改，持续改进\n"
        if low > 0:
            summary += f"🟢 低风险缺口：{low} 个 — 持续改进\n"

        summary += f"\n合规评分：{score}/100\n"

        if score >= 80:
            summary += "评分良好，建议针对剩余缺口制定整改计划。"
        elif score >= 60:
            summary += "评分一般，需尽快整改高风险缺口。"
        else:
            summary += "评分较低，建议立即启动合规整改工作。"

        return summary