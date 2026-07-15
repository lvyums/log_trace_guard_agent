"""全局配置管理 — 所有硬编码配置统一收口"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from enum import Enum


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
    llm_api_key: str = "webray-key-6c3c51b69d2b28e1635295d442297ab6"
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
    chroma_db_path: str = "./data/chroma_db"
    top_k_retrieval: int = 5
    similarity_threshold: float = 0.6

    # ── 日志解析配置 ──
    max_log_length: int = 10000
    max_batch_size: int = 100
    min_log_length: int = 1
    log_clean_syslog: bool = True

    # ── 文件上传配置 ──
    max_upload_size_mb: int = 10
    upload_temp_dir: str = "./data/upload_temp"
    allowed_extensions: list[str] = [".txt", ".csv", ".log"]

    # ── 接口超时配置 ──
    api_timeout: int = 30

    # ── 风险研判配置 ──
    risk_confidence_high: float = 0.85
    risk_confidence_medium: float = 0.70
    risk_confidence_low: float = 0.50

    # ── 规则引擎配置 ──
    rule_data_dir: str = "./data/rule_data"
    rule_watcher_enabled: bool = True

    # ── 模块三：日志采集配置 ──
    device_protocol_data_path: str = "./data/rule_data/device_protocol.json"
    fault_kb_data_path: str = "./data/rule_data/fault_kb.json"
    collect_template_data_path: str = "./data/rule_data/collect_templates.json"
    context_ttl_seconds: int = 3600  # 上下文过期时间（秒）
    match_confidence_threshold: float = 60.0  # 设备匹配置信度阈值
    # 架构分级阈值
    arch_small_device_count: int = 10
    arch_small_log_volume: str = "small"
    arch_medium_device_count: int = 100

    # ── 模块二：合规审计配置 ──
    compliance_standards_data_path: str = "./data/rule_data/compliance_standards.json"
    compliance_baselines_data_path: str = "./data/rule_data/compliance_baselines.json"

    # ── 模块五：交互式实训配置 ──
    training_scenarios_data_path: str = "./data/rule_data/training_scenarios.json"
    training_standard_answers_data_path: str = "./data/rule_data/training_standard_answers.json"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()