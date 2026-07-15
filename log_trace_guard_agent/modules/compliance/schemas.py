"""模块二：合规审计基线模块 — 请求/响应 Pydantic Schema"""

from pydantic import BaseModel, Field
from typing import Optional


# ── 合规标准智能问答 ──

class ComplianceQAReq(BaseModel):
    """合规标准问答请求"""
    question: str = Field(..., max_length=2000, description="合规相关问题，如：日志留存需要多久、等保三级有哪些要求")
    asset_type: Optional[str] = Field(default=None, max_length=200, description="资产类型约束（可选）")
    standard_filter: Optional[str] = Field(default=None, max_length=200, description="标准筛选（等保/网安法/数安法）")


class ComplianceStandardItem(BaseModel):
    """单条合规标准条目"""
    item_id: str = Field(default="", description="标准条目编号")
    requirement: str = Field(default="", description="合规要求")
    detail: str = Field(default="", description="详细说明")
    check_method: str = Field(default="", description="检查方法")
    risk_if_not: str = Field(default="", description="不符合风险")
    applicable_devices: list[str] = Field(default_factory=list, description="适用设备")


class ComplianceStandard(BaseModel):
    """合规标准"""
    standard_id: str = Field(default="", description="标准编号")
    name: str = Field(default="", description="标准名称")
    category: str = Field(default="", description="标准分类")
    items: list[ComplianceStandardItem] = Field(default_factory=list, description="标准条目列表")


class ComplianceQAResp(BaseModel):
    """合规标准问答响应"""
    answer: str = Field(default="", description="问题回答")
    standards: list[ComplianceStandard] = Field(default_factory=list, description="相关标准引用")
    matched_count: int = Field(default=0, description="匹配标准条目数")
    note: Optional[str] = Field(default=None, description="补充说明")


# ── 合规基线自动生成 ──

class BaselineGenReq(BaseModel):
    """合规基线生成请求"""
    asset_count: int = Field(default=10, ge=1, le=100000, description="资产数量（服务器+设备总数）")
    business_type: str = Field(default="enterprise", max_length=100, description="业务类型：enterprise/gov/education/finance/medical/other")
    device_types: list[str] = Field(default_factory=list, max_length=50, description="设备类型列表，如：ssh,web,firewall,db,server")
    monitor_scenarios: Optional[list[str]] = Field(default=None, max_length=20, description="需监控的场景列表（可选，默认全场景）")
    industry: Optional[str] = Field(default=None, max_length=100, description="行业（如：教育/政企/金融/医疗）")


class BaselineThreshold(BaseModel):
    """基线阈值项"""
    name: str = Field(default="", description="阈值名称")
    description: str = Field(default="", description="阈值描述")
    severity: str = Field(default="medium", description="严重等级")


class MonitorBaseline(BaseModel):
    """单条监控基线"""
    baseline_id: str = Field(default="", description="基线编号")
    name: str = Field(default="", description="基线名称")
    category: str = Field(default="", description="基线分类")
    description: str = Field(default="", description="基线描述")
    monitor_scenario: str = Field(default="", description="监控场景")
    thresholds: list[BaselineThreshold] = Field(default_factory=list, description="阈值列表")
    check_frequency: str = Field(default="", description="检查频率")
    alert_standard: str = Field(default="", description="告警标准")
    applicable_devices: list[str] = Field(default_factory=list, description="适用设备")
    severity: str = Field(default="", description="严重等级")
    remediation: str = Field(default="", description="整改建议")


class BaselineGenResp(BaseModel):
    """合规基线生成响应"""
    baselines: list[MonitorBaseline] = Field(default_factory=list, description="监控基线列表")
    summary: str = Field(default="", description="基线总结")
    note: Optional[str] = Field(default=None, description="补充说明")


# ── 合规自查与缺口整改 ──

class ComplianceCheckReq(BaseModel):
    """合规自查请求"""
    log_retention_days: Optional[int] = Field(default=None, ge=1, description="当前日志留存天数")
    has_backup: Optional[bool] = Field(default=None, description="是否有日志备份")
    has_tamper_proof: Optional[bool] = Field(default=None, description="是否启用防篡改")
    backup_frequency: Optional[str] = Field(default=None, max_length=100, description="备份频率")
    device_count: Optional[int] = Field(default=None, ge=1, description="设备数量")
    has_audit_mechanism: Optional[bool] = Field(default=None, description="是否有审计机制")
    has_ntp: Optional[bool] = Field(default=None, description="是否启用NTP时钟同步")
    audit_frequency: Optional[str] = Field(default=None, max_length=100, description="审计频率")
    has_alert_system: Optional[bool] = Field(default=None, description="是否有实时告警系统")
    has_bastion: Optional[bool] = Field(default=None, description="是否有堡垒机")
    additional_info: Optional[str] = Field(default=None, max_length=2000, description="补充信息")


class ComplianceGap(BaseModel):
    """合规缺口"""
    gap_id: str = Field(default="", description="缺口编号")
    standard_ref: str = Field(default="", description="引用标准")
    requirement: str = Field(default="", description="合规要求")
    current_status: str = Field(default="", description="当前状态")
    risk_level: str = Field(default="", description="风险等级")
    risk_description: str = Field(default="", description="风险说明")
    remediation_steps: list[str] = Field(default_factory=list, description="整改步骤")
    priority: str = Field(default="", description="修复优先级")


class ComplianceCheckResp(BaseModel):
    """合规自查响应"""
    gaps: list[ComplianceGap] = Field(default_factory=list, description="合规缺口列表")
    summary: str = Field(default="", description="自查总结")
    overall_score: int = Field(default=0, ge=0, le=100, description="合规评分 0-100")
    critical_count: int = Field(default=0, description="高风险缺口数")
    medium_count: int = Field(default=0, description="中风险缺口数")
    low_count: int = Field(default=0, description="低风险缺口数")
    note: Optional[str] = Field(default=None, description="补充说明")