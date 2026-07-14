"""全局配置管理 — 所有硬编码配置统一收口"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from enum import Enum


class RiskLevel(str, Enum):
    """统一风险枚举"""
    P0_HIGH = "P0_高危"
    P1_MEDIUM = "P1_中危"
    P2_LOW = "P2_低危"
    P3_NOISE = "P3_噪音"


class Settings(BaseSettings):
    # ── 服务配置 ──
    service_host: str = "0.0.0.0"
    service_port: int = 8000
    service_reload: bool = True

    # ── LLM 配置 ──
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com"
    llm_model_name: str = "deepseek-chat"
    llm_light_model_name: str = "deepseek-chat"
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

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()