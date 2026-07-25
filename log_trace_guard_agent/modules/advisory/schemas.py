"""规划咨询模块 — 数据模型"""

from typing import Optional
from pydantic import BaseModel, Field


class ArchitectureRecommendReq(BaseModel):
    """架构推荐请求"""
    device_count: int = Field(..., ge=1, description="设备数量")
    daily_log_volume: str = Field(..., description="日志量级: small/medium/large")
    budget: str = Field(default="low", description="预算: low/medium/high")
    team_skill: str = Field(default="basic", description="团队技能: basic/intermediate/advanced")


class PlatformChooseReq(BaseModel):
    """平台选型请求"""
    device_count: int = Field(..., ge=1, description="设备数量")
    daily_log_volume: str = Field(default="medium", description="日志量级: small/medium/large")
    budget: str = Field(default="medium", description="预算: low/medium/high")
    team_skill: str = Field(default="basic", description="团队技能: basic/intermediate/advanced")
    requirements: Optional[list[str]] = Field(default=None, description="特殊需求列表")


class GuideGenerateReq(BaseModel):
    """指导手册生成请求"""
    scale: str = Field(..., description="企业规模: small/medium/large")
    device_types: list[str] = Field(..., description="安全设备类型列表")
    device_count: int = Field(..., ge=1, description="设备数量")
    daily_log_volume: str = Field(default="medium", description="日志量级: small/medium/large")
    budget: str = Field(default="medium", description="预算: low/medium/high")
    team_skill: str = Field(default="basic", description="团队技能: basic/intermediate/advanced")
    collect_plans: Optional[list[dict]] = Field(default=None, description="采集方案结果")
    architecture: Optional[dict] = Field(default=None, description="架构推荐结果")
    platform: Optional[dict] = Field(default=None, description="平台选型结果")


class ArchitectureRecommendResp(BaseModel):
    """架构推荐响应"""
    recommended_arch: str
    architecture_desc: str
    device_count: int
    daily_log_volume: str


class PlatformRecommendResp(BaseModel):
    """平台选型响应"""
    recommendation: dict
    alternatives: list[dict]
    summary: str
