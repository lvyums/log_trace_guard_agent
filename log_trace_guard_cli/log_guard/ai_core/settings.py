"""AI Core 配置管理 — 加载 .env / ~/.log-guard/config.json / 环境变量"""
import os
import json
import pathlib
from typing import Optional


def _get_config_dir() -> str:
    """获取 ~/.log-guard/ 配置目录"""
    home = os.path.expanduser("~")
    cfg_dir = os.path.join(home, ".log-guard")
    os.makedirs(cfg_dir, exist_ok=True)
    return cfg_dir


def _load_dotenv(path: str) -> dict:
    """简易 .env 解析（不依赖 python-dotenv 也能工作）"""
    result = {}
    if not os.path.isfile(path):
        return result
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key, val = key.strip(), val.strip().strip("\"'").strip()
            if key:
                result[key] = val
    return result


class AISettings:
    """AI Core 全局配置 — 分层加载（环境变量 > .env > ~/.log-guard/config.json）"""

    def __init__(self):
        # ── 1. 默认值 ──
        self.llm_api_key: str = ""
        self.llm_base_url: str = "https://raytoken.com.cn/v1"
        self.llm_model_name: str = "deepseek-v4-flash"
        self.llm_temperature: float = 0.1
        self.llm_timeout: int = 30
        self.llm_max_tokens: int = 2048

        self.embedding_model: str = "text-embedding-3-small"
        self.vector_cache_file: str = "rule_vector_cache.json"
        self.rag_top_k: int = 5
        self.rag_similarity_threshold: float = 0.60

        self.intent_confidence_threshold: float = 0.40
        self.max_context_turns: int = 20
        self.chat_log_dir: str = "chat_logs"

        # ── 2. 加载分层配置 ──
        self._load_from_config_json()
        self._load_from_dotenv()
        self._load_from_env()

    def _load_from_config_json(self):
        """加载 ~/.log-guard/config.json"""
        cfg_dir = _get_config_dir()
        cfg_path = os.path.join(cfg_dir, "config.json")
        if os.path.isfile(cfg_path):
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._apply_dict(data)
            except Exception:
                pass

    def _load_from_dotenv(self):
        """加载项目目录 .env"""
        # 尝试多个位置
        candidates = [
            os.path.join(os.getcwd(), ".env"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"),
        ]
        for path in candidates:
            if os.path.isfile(path):
                data = _load_dotenv(path)
                if data:
                    self._apply_dict(data)
                    break

    def _load_from_env(self):
        """加载环境变量（最高优先级）"""
        mapping = {
            "LLM_API_KEY": "llm_api_key",
            "LLM_BASE_URL": "llm_base_url",
            "LLM_MODEL_NAME": "llm_model_name",
            "LLM_TEMPERATURE": "llm_temperature",
            "LLM_TIMEOUT": "llm_timeout",
            "LLM_MAX_TOKENS": "llm_max_tokens",
            "EMBEDDING_MODEL": "embedding_model",
            "RAG_TOP_K": "rag_top_k",
            "RAG_SIMILARITY_THRESHOLD": "rag_similarity_threshold",
        }
        for env_key, attr in mapping.items():
            val = os.environ.get(env_key)
            if val is not None:
                try:
                    current = getattr(self, attr)
                    if isinstance(current, float):
                        setattr(self, attr, float(val))
                    elif isinstance(current, int):
                        setattr(self, attr, int(val))
                    else:
                        setattr(self, attr, val)
                except (ValueError, TypeError):
                    setattr(self, attr, val)

    def _apply_dict(self, data: dict):
        """将 dict 中的值应用到同名属性"""
        for key, val in data.items():
            # 兼容 LLM_API_KEY 和 llm_api_key 两种写法
            attr = key.lower()
            if hasattr(self, attr) and val is not None:
                current = getattr(self, attr)
                if isinstance(current, bool):
                    setattr(self, attr, str(val).lower() in ("true", "1", "yes"))
                elif isinstance(current, float):
                    try:
                        setattr(self, attr, float(val))
                    except (ValueError, TypeError):
                        setattr(self, attr, val)
                elif isinstance(current, int):
                    try:
                        setattr(self, attr, int(val))
                    except (ValueError, TypeError):
                        setattr(self, attr, val)
                else:
                    setattr(self, attr, val)

    def save_config(self):
        """保存当前配置到 ~/.log-guard/config.json"""
        cfg_dir = _get_config_dir()
        cfg_path = os.path.join(cfg_dir, "config.json")
        data = {
            "llm_api_key": self.llm_api_key,
            "llm_base_url": self.llm_base_url,
            "llm_model_name": self.llm_model_name,
            "llm_temperature": self.llm_temperature,
            "llm_timeout": self.llm_timeout,
            "llm_max_tokens": self.llm_max_tokens,
        }
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return cfg_path

    @property
    def is_configured(self) -> bool:
        """检查 LLM API Key 是否已配置"""
        return bool(self.llm_api_key)

    @property
    def config_dir(self) -> str:
        return _get_config_dir()

    @property
    def chat_log_dir_path(self) -> str:
        path = os.path.join(self.config_dir, self.chat_log_dir)
        os.makedirs(path, exist_ok=True)
        return path

    @property
    def vector_cache_path(self) -> str:
        return os.path.join(self.config_dir, self.vector_cache_file)


settings = AISettings()