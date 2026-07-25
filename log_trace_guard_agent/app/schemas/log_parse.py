"""统一接口入参/出参模型层 — Pydantic 定义所有接口结构体"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional


def _validate_log_line(v: str) -> str:
    """共享的日志行校验逻辑"""
    if not v or not v.strip():
        raise ValueError("日志内容不能为空")
    return v.strip()


class LogIdentifyReq(BaseModel):
    """日志类型识别请求"""
    log_line: str = Field(default="", max_length=10000, description="日志内容")
    input_type: str = Field(default="text", pattern="^(text|file|scene)$", description="输入类型")

    _validate_log_line = field_validator("log_line")(_validate_log_line)


class LogIdentifyResp(BaseModel):
    """日志类型识别响应"""
    device_type: str = Field(default="", description="设备类型")
    confidence: float = Field(default=0.0, description="识别置信度 0-100")
    identify_reason: str = Field(default="", description="识别依据说明")


class LogParseReq(BaseModel):
    """日志解析请求"""
    log_line: str = Field(default="", max_length=10000, description="日志内容")

    _validate_log_line = field_validator("log_line")(_validate_log_line)


class LogParseResp(BaseModel):
    """日志解析响应"""
    timestamp: Optional[str] = None
    src_ip: Optional[str] = None
    dst_ip: Optional[str] = None
    src_port: Optional[str] = None
    dst_port: Optional[str] = None
    user: Optional[str] = None
    url: Optional[str] = None
    method: Optional[str] = None
    command: Optional[str] = None
    status: Optional[str] = None
    device_type: Optional[str] = None
    missing_fields: list[str] = Field(default_factory=list, description="缺失字段列表")


class RiskAssessReq(BaseModel):
    """风险研判请求"""
    log_line: str = Field(default="", max_length=10000, description="日志内容")
    device_type: Optional[str] = Field(default=None, description="设备类型（可选，提高研判精度）")

    _validate_log_line = field_validator("log_line")(_validate_log_line)


class RiskAssessResp(BaseModel):
    """风险研判响应"""
    risk_level: str = Field(default="", description="风险等级: P0高危/P1中危/P2低危/P3噪音")
    confidence: float = Field(default=0.0, description="置信度 0-100")
    attack_type: Optional[str] = None
    risk_desc: Optional[str] = None
    match_rule_ids: list[str] = Field(default_factory=list, description="命中规则ID列表")
    suggestion: Optional[str] = None


class FieldExplainReq(BaseModel):
    """字段释义请求"""
    field_name: str = Field(default="", max_length=200, description="字段名称")
    device_type: Optional[str] = Field(default=None, description="日志设备类型上下文（可选）")


class FieldExplainBatchReq(BaseModel):
    """批量字段释义请求"""
    field_names: list[str] = Field(..., min_length=1, max_length=20, description="字段名称列表")
    device_type: Optional[str] = Field(default=None, description="日志设备类型上下文（可选）")


class FieldExplainResp(BaseModel):
    """字段释义响应"""
    field: str
    explanation: str
    device_type: Optional[str] = None


class BatchParseReq(BaseModel):
    """批量解析请求"""
    logs: list[str] = Field(..., min_length=1, max_length=100, description="日志列表")
    assess: bool = Field(default=False, description="是否同时进行风险研判")


class BatchFileParseReq(BaseModel):
    """批量文件解析请求"""
    file_paths: list[str] = Field(..., min_length=1, description="服务端文件路径列表")
    assess: bool = Field(default=False, description="是否同时进行风险研判")


class BatchParseItem(BaseModel):
    """批量解析单条结果"""
    index: int
    log_line: str
    parse_result: Optional[LogParseResp] = None
    risk_result: Optional[RiskAssessResp] = None
    error: Optional[str] = None


class BatchParseResp(BaseModel):
    """批量解析响应"""
    total: int
    success_count: int
    fail_count: int
    items: list[BatchParseItem]
    risk_summary: Optional[dict] = None