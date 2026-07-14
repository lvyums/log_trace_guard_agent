"""日志采集架构指导模块 — 接口数据模型"""

from pydantic import BaseModel, Field
from typing import Optional


class DeviceMatchReq(BaseModel):
    """设备类型匹配请求"""
    device_type: str = Field(..., max_length=50, description="设备类型")
    device_model: str = Field(default="", max_length=100, description="设备型号（可选）")
    scale: str = Field(default="small", pattern="^(small|medium|large)$", description="企业规模")


class DeviceMatchResp(BaseModel):
    """设备类型匹配响应"""
    device_info: dict = Field(default_factory=dict, description="设备信息")
    plan: Optional[dict] = Field(default=None, description="采集方案")
    match_source: str = Field(default="", description="匹配来源: model / type")


class CollectPlanReq(BaseModel):
    """采集方案生成请求"""
    device_type: str = Field(..., max_length=50, description="设备类型")
    device_model: str = Field(default="", max_length=100, description="设备型号（可选）")
    scale: str = Field(default="small", pattern="^(small|medium|large)$", description="企业规模")
    include_config: bool = Field(default=True, description="是否包含配置模板")


class CollectPlanResp(BaseModel):
    """采集方案响应"""
    device_type: str
    device_model: str = ""
    protocol: str = ""
    architecture: str = ""
    config_template: dict = Field(default_factory=dict)
    steps: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class FaultDiagnoseReq(BaseModel):
    """故障诊断请求"""
    symptom: str = Field(..., max_length=500, description="故障症状描述")
    device_type: Optional[str] = Field(default=None, max_length=50, description="设备类型（可选）")


class FaultDiagnoseResp(BaseModel):
    """故障诊断响应"""
    fault_type: str
    fault_desc: str
    possible_causes: list[str] = Field(default_factory=list)
    fix_steps: list[str] = Field(default_factory=list)
    prevention: list[str] = Field(default_factory=list)
    severity: str = "medium"


class ArchitectureRecommendReq(BaseModel):
    """架构推荐请求"""
    device_count: int = Field(..., ge=1, description="设备数量")
    daily_log_volume: str = Field(default="small", pattern="^(small|medium|large)$", description="日志量级")
    budget: str = Field(default="low", pattern="^(low|medium|high)$", description="预算水平")
    team_skill: str = Field(default="basic", pattern="^(basic|intermediate|advanced)$", description="运维能力")


class ArchitectureRecommendResp(BaseModel):
    """架构推荐响应"""
    recommended_arch: str = Field(default="", description="推荐架构")
    architecture_desc: str = Field(default="", description="架构描述")
    components: list[str] = Field(default_factory=list, description="核心组件")
    data_flow: list[str] = Field(default_factory=list, description="数据流向")
    estimated_cost: str = Field(default="", description="估算成本")
    pros: list[str] = Field(default_factory=list, description="优势")
    cons: list[str] = Field(default_factory=list, description="劣势")
