"""全局配置管理 — 所有硬编码配置统一收口"""

import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from enum import Enum

# 项目根目录：settings.py 所在目录的上级（即 log_trace_guard_agent/）
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class RiskLevel(str, Enum):
    """统一风险枚举"""
    P0_HIGH = "P0_高危"
    P1_MEDIUM = "P1_中危"
    P2_LOW = "P2_低危"
    P3_NOISE = "P3_噪音"


class DeviceType(str, Enum):
    """设备类型枚举"""
    FIREWALL = "firewall"
    WAF = "waf"
    IDS = "ids"
    IPS = "ips"
    ROUTER = "router"
    SWITCH = "switch"
    SERVER = "server"
    WEB = "web"
    APPLICATION = "application"
    NGINX = "nginx"
    APACHE = "apache"
    DB = "db"
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    SQLSERVER = "sqlserver"
    ORACLE = "oracle"
    BASTION = "bastion"
    HIDS = "hids"
    EDR = "edr"
    SIEM = "siem"
    UNKNOWN = "unknown"


class CollectProtocol(str, Enum):
    """采集协议枚举"""
    SYSLOG = "syslog"
    FILE = "file"
    DB_SYNC = "db_sync"
    AGENT = "agent"
    API = "api"


class ScaleLevel(str, Enum):
    """企业规模枚举"""
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class Settings(BaseSettings):
    # ── 服务配置 ──
    service_host: str = "0.0.0.0"
    service_port: int = 8000
    service_reload: bool = True

    # ── LLM 配置 ──
    llm_api_key: str = ""
    llm_base_url: str = "https://raytoken.com.cn/v1"
    llm_model_name: str = "deepseek-v4-flash"
    llm_light_model_name: str = "deepseek-v4-flash"
    llm_temperature: float = 0.1
    llm_timeout: int = 10
    llm_retry_count: int = 1
    llm_retry_interval: float = 1.0

    # ── 向量库配置 ──
    embedding_model: str = "BAAI/bge-large-zh-v1.5"
    reranker_model: str = "BAAI/bge-reranker-large"
    chroma_db_path: str = os.path.join(_PROJECT_ROOT, "data", "chroma_db")
    top_k_retrieval: int = 5
    similarity_threshold: float = 0.6

    # ── 日志解析配置 ──
    max_log_length: int = 10000
    max_batch_size: int = 100
    min_log_length: int = 1
    log_clean_syslog: bool = True

    # ── 文件上传配置 ──
    max_upload_size_mb: int = 10
    upload_temp_dir: str = os.path.join(_PROJECT_ROOT, "data", "upload_temp")
    allowed_extensions: list[str] = [".txt", ".csv", ".log"]

    # ── 接口超时配置 ──
    api_timeout: int = 30

    # ── 风险研判配置 ──
    risk_confidence_high: float = 0.85
    risk_confidence_medium: float = 0.70
    risk_confidence_low: float = 0.50

    # ── Splunk 配置 ──
    splunk_base_url: str = ""          # 如 https://splunk.company.com
    splunk_username: str = ""          # 用户名（Token 认证时可为空）
    splunk_password: str = ""          # 密码（Token 认证时可为空）
    splunk_auth_token: str = ""        # Bearer Token（优先于用户名密码）
    splunk_verify_ssl: bool = True     # 是否验证 SSL 证书
    splunk_search_timeout: int = 30    # 查询超时（秒）
    splunk_max_results: int = 100      # 最大返回条数

    # ── 规则引擎配置 ──
    rule_data_dir: str = os.path.join(_PROJECT_ROOT, "data", "rule_data")
    rule_watcher_enabled: bool = True

    # ── 模块三：日志采集配置 ──
    device_protocol_data_path: str = os.path.join(_PROJECT_ROOT, "data", "rule_data", "device_protocol.json")
    fault_kb_data_path: str = os.path.join(_PROJECT_ROOT, "data", "rule_data", "fault_kb.json")
    collect_template_data_path: str = os.path.join(_PROJECT_ROOT, "data", "rule_data", "collect_templates.json")
    context_ttl_seconds: int = 3600  # 上下文过期时间（秒）
    match_confidence_threshold: float = 60.0  # 设备匹配置信度阈值
    # 架构分级阈值
    arch_small_device_count: int = 10
    arch_small_log_volume: str = "small"
    arch_medium_device_count: int = 100

    # ── 模块二：合规审计配置 ──
    compliance_standards_data_path: str = os.path.join(_PROJECT_ROOT, "data", "rule_data", "compliance_standards.json")
    compliance_baselines_data_path: str = os.path.join(_PROJECT_ROOT, "data", "rule_data", "compliance_baselines.json")

    # ── 模块五：交互式实训配置 ──
    training_scenarios_data_path: str = os.path.join(_PROJECT_ROOT, "data", "rule_data", "training_scenarios.json")
    training_standard_answers_data_path: str = os.path.join(_PROJECT_ROOT, "data", "rule_data", "training_standard_answers.json")

    model_config = SettingsConfigDict(
        env_file=os.path.join(_PROJECT_ROOT, ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def model_post_init(self, __context):
        """将所有相对路径修正为基于项目根目录的绝对路径"""
        def _resolve(path: str) -> str:
            if os.path.isabs(path):
                return path
            return os.path.normpath(os.path.join(_PROJECT_ROOT, path))

        self.rule_data_dir = _resolve(self.rule_data_dir)
        self.chroma_db_path = _resolve(self.chroma_db_path)
        self.upload_temp_dir = _resolve(self.upload_temp_dir)
        self.device_protocol_data_path = _resolve(self.device_protocol_data_path)
        self.fault_kb_data_path = _resolve(self.fault_kb_data_path)
        self.collect_template_data_path = _resolve(self.collect_template_data_path)
        self.compliance_standards_data_path = _resolve(self.compliance_standards_data_path)
        self.compliance_baselines_data_path = _resolve(self.compliance_baselines_data_path)
        self.training_scenarios_data_path = _resolve(self.training_scenarios_data_path)
        self.training_standard_answers_data_path = _resolve(self.training_standard_answers_data_path)


settings = Settings()