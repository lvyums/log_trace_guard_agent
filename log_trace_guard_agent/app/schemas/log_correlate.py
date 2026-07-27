"""日志联合审查 — 请求/响应模型"""

from pydantic import BaseModel, Field
from typing import Optional


class CorrelateLogsReq(BaseModel):
    """日志关联分析请求"""
    log_lines: list[str] = Field(default_factory=list, min_length=1, description="日志行列表")
    time_window_minutes: int = Field(default=5, ge=1, le=1440, description="关联时间窗口（分钟）")
    use_llm: bool = Field(default=False, description="是否强制使用 LLM 分析（跳过关键词匹配）")
    detailed: bool = Field(default=False, description="是否返回详细事件信息")


class FileCrunchReq(BaseModel):
    """日志文件分析请求"""
    file_path: Optional[str] = Field(default=None, description="服务器上的文件路径（仅单个文件）")
    file_paths: list[str] = Field(default_factory=list, description="服务器上的多文件路径（多源日志联合分析）")
    file_content: Optional[str] = Field(default=None, description="直接传入文件内容（替代 file_path）")
    time_window_minutes: int = Field(default=5, ge=1, le=1440, description="关联时间窗口（分钟）")
    use_llm: bool = Field(default=False, description="是否强制使用 LLM 分析")


class ToTraceReq(BaseModel):
    """攻击链 → 攻击溯源脚本 请求"""
    log_lines: list[str] = Field(..., min_length=1, description="攻击链相关的日志行")
    chain_name: str = Field(default="", description="攻击链名称")
    attack_type: str = Field(default="unknown", description="攻击类型")
    pre_analyzed: Optional[dict] = Field(default=None, description="关联分析已检出的信息（matched_keywords, indicators, matched_line_indices 等），避免重复解析")


class ToScenarioReq(BaseModel):
    """攻击链 → 实训场景 请求"""
    log_lines: list[str] = Field(..., min_length=1, description="攻击链相关的日志行")
    chain_name: str = Field(default="", description="攻击链名称")
    chain_description: str = Field(default="", description="攻击链描述")
    chain_data: Optional[dict] = Field(default=None, description="攻击链完整数据（含 temporal 字段），用于生成动态实训场景")


class CorrelateResp(BaseModel):
    """日志关联分析响应"""
    total_events: int = Field(default=0, description="总事件数")
    chains: list[dict] = Field(default_factory=list, description="检测到的攻击链")
    summary: str = Field(default="", description="分析摘要")
    method: str = Field(default="keyword", description="分析方法：keyword / llm / hybrid")
    matched_keywords: list[str] = Field(default_factory=list, description="命中的关键词（keyword 模式）")


class PatternItem(BaseModel):
    """攻击链模式条目"""
    id: Optional[str] = None
    name: str = ""
    risk_level: str = ""
    stages: list[str] = Field(default_factory=list)


class PatternListResp(BaseModel):
    """攻击链模式列表响应"""
    patterns: list[PatternItem] = Field(default_factory=list)
