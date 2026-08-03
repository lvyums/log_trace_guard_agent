"""模块四：技术赋能脚本生成 — 请求/响应 Pydantic Schema"""

from pydantic import BaseModel, Field
from typing import Optional


# ── 正则生成 ──

class RegexGenReq(BaseModel):
    """正则规则生成请求"""
    scenario: str = Field(..., max_length=2000, description="攻防场景描述，如：SSH爆破、SQL注入、端口扫描")
    log_sample: Optional[str] = Field(default=None, max_length=5000, description="日志样例（可选，用于精准匹配）")
    device_type: Optional[str] = Field(default=None, description="设备类型上下文（ssh/web/waf/firewall/db）")


class RegexGenItem(BaseModel):
    """单条正则规则"""
    name: str = Field(default="", description="规则名称")
    pattern: str = Field(default="", description="正则表达式")
    description: str = Field(default="", description="规则说明")
    match_example: Optional[str] = Field(default=None, description="匹配示例")
    priority: int = Field(default=50, ge=0, le=100, description="优先级 0-100")


class RegexGenResp(BaseModel):
    """正则规则生成响应"""
    regexes: list[RegexGenItem]
    scenario: str
    note: Optional[str] = None


# ── ES 检索语句生成 ──

class ESQueryGenReq(BaseModel):
    """ES 检索语句生成请求"""
    search_scenario: str = Field(..., max_length=2000, description="检索场景描述")
    index_pattern: Optional[str] = Field(default=None, description="ES 索引名称模式")
    time_range: Optional[str] = Field(default=None, description="时间范围，如：last_24h / last_7d / custom")
    filters: Optional[dict] = Field(default=None, description="附加过滤条件")


class ESQueryGenResp(BaseModel):
    """ES 检索语句生成响应"""
    query: str = Field(default="", description="生成的 ES Query DSL JSON")
    explanation: str = Field(default="", description="查询逻辑说明")
    scenario: str
    index_pattern: Optional[str] = None
    note: Optional[str] = None



# ── 攻击链路溯源 ──

class TraceLinkReq(BaseModel):
    """攻击链路溯源请求"""
    logs: list[str] = Field(..., min_length=1, max_length=100, description="日志列表（多条日志）")
    attack_type: Optional[str] = Field(default=None, description="已知攻击类型（可选）")
    start_time: Optional[str] = Field(default=None, description="开始时间")
    end_time: Optional[str] = Field(default=None, description="结束时间")


class TraceEvent(BaseModel):
    """溯源事件节点"""
    timestamp: Optional[str] = None
    event_type: str = Field(default="", description="事件类型")
    source: str = Field(default="", description="源 IP/资产")
    target: Optional[str] = Field(default=None, description="目标 IP/资产")
    action: str = Field(default="", description="行为描述")
    risk_level: str = Field(default="info", description="风险等级")
    detail: Optional[str] = Field(default=None, description="详细信息")


class TraceLinkResp(BaseModel):
    """攻击链路溯源响应"""
    attack_chain: list[TraceEvent] = Field(default_factory=list, description="攻击链路事件链")
    entry_point: Optional[str] = Field(default=None, description="攻击入口")
    affected_assets: list[str] = Field(default_factory=list, description="受影响资产")
    attack_stage: str = Field(default="", description="攻击阶段判定")
    summary: str = Field(default="", description="溯源总结")


# ── 脚本优化纠错 ──

class OptimizeReq(BaseModel):
    """脚本优化纠错请求"""
    script: str = Field(..., max_length=10000, description="用户提交的脚本/正则/检索语句")
    script_type: str = Field(default="regex", pattern="^(regex|es_query|sql)$", description="脚本类型")
    scenario: Optional[str] = Field(default=None, description="场景描述")


class OptimizeResp(BaseModel):
    """脚本优化纠错响应"""
    original: str = Field(default="", description="原始脚本")
    optimized: str = Field(default="", description="优化后的脚本")
    issues: list[str] = Field(default_factory=list, description="发现的问题列表")
    explanation: str = Field(default="", description="优化说明")
    score: int = Field(default=0, ge=0, le=100, description="原始脚本评分 0-100")


# ── Splunk 查询 ──

class SplunkConfigParam(BaseModel):
    """前端传入的 Splunk 连接配置"""
    base_url: str = Field(..., description="Splunk 服务器地址")
    auth_token: Optional[str] = Field(default=None, description="Bearer Token")
    username: Optional[str] = Field(default=None, description="用户名")
    password: Optional[str] = Field(default=None, description="密码")
    verify_ssl: bool = Field(default=True, description="验证 SSL 证书")


class SplunkSearchReq(BaseModel):
    """Splunk 查询请求"""
    spl_query: str = Field(default="", max_length=5000, description="Splunk SPL 查询语句（测试连接时可为空）")
    max_results: Optional[int] = Field(default=None, ge=1, le=1000, description="最大返回条数")
    splunk_config: Optional[SplunkConfigParam] = Field(default=None, description="Splunk 连接配置（有值时覆盖后端默认配置）")


class SplunkSearchResp(BaseModel):
    """Splunk 查询响应"""
    results: list[dict] = Field(default_factory=list, description="查询结果")
    sid: str = Field(default="", description="搜索任务 ID")
    event_count: int = Field(default=0, description="匹配事件总数")
    open_url: str = Field(default="", description="Splunk Web UI 跳转链接")
    execution_time: float = Field(default=0.0, description="执行耗时（秒）")


# ── ES 查询 ──

class ESConfigParam(BaseModel):
    """前端传入的 ES 连接配置"""
    base_url: str = Field(..., description="ES 服务器地址，如 http://localhost:9200")
    username: Optional[str] = Field(default=None, description="用户名")
    password: Optional[str] = Field(default=None, description="密码")
    verify_ssl: bool = Field(default=True, description="验证 SSL 证书")
    max_results: int = Field(default=100, ge=1, le=10000, description="最大返回条数")


class ESSearchReq(BaseModel):
    """ES 查询请求"""
    query_dsl: str = Field(default="", max_length=20000, description="ES Query DSL JSON 字符串（测试连接时可为空）")
    index_pattern: Optional[str] = Field(default=None, description="索引名称模式")
    max_results: Optional[int] = Field(default=None, ge=1, le=10000, description="最大返回条数")
    es_config: Optional[ESConfigParam] = Field(default=None, description="ES 连接配置（覆盖后端默认配置）")


class ESConfigSaveReq(BaseModel):
    """ES 配置保存请求（写入 .env）"""
    es_base_url: str = Field(..., description="ES 地址")
    es_username: Optional[str] = Field(default=None, description="用户名")
    es_password: Optional[str] = Field(default=None, description="密码")
    es_verify_ssl: bool = Field(default=True, description="验证 SSL")
    es_max_results: int = Field(default=100, description="最大返回条数")


# ── 批量请求 ──

class BatchRegexGenReq(BaseModel):
    """批量正则规则生成请求"""
    scenarios: list[RegexGenReq] = Field(..., min_length=1, max_length=20, description="批量场景列表")


class BatchESQueryGenReq(BaseModel):
    """批量 ES 检索语句生成请求"""
    queries: list[ESQueryGenReq] = Field(..., min_length=1, max_length=20, description="批量检索请求")