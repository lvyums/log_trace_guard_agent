"""
Standalone utility module for log_guard_cli.

Provides Result, JsonConfigLoader, LogManager, and str_util utilities.
"""

import json
import logging
import os
import re
import threading
import time
from logging.handlers import RotatingFileHandler
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Result — Unified API response format
# ---------------------------------------------------------------------------


class Result:
    """Unified API response format with {code, msg, data, timestamp}."""

    @staticmethod
    def ok(data: Any = None, msg: str = "success") -> dict:
        return {
            "code": 0,
            "msg": msg,
            "data": data or {},
            "timestamp": int(time.time() * 1000),
        }

    @staticmethod
    def fail(msg: str, code: int = 400, data: Any = None) -> dict:
        return {
            "code": code,
            "msg": msg,
            "data": data or {},
            "timestamp": int(time.time() * 1000),
        }

    @staticmethod
    def from_exception(code: int, msg: str) -> dict:
        return {
            "code": code,
            "msg": msg,
            "data": {},
            "timestamp": int(time.time() * 1000),
        }


# ---------------------------------------------------------------------------
# JsonConfigLoader — Singleton JSON config loader with cache
# ---------------------------------------------------------------------------

# Compute DATA_DIR relative to this file's location:
# log_guard/common/utils.py → log_guard/data/rule_data/
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(_THIS_DIR), "data", "rule_data")


class JsonConfigLoader:
    """Thread-safe singleton JSON config loader with in-memory cache.

    Usage:
        config = JsonConfigLoader.load("risk_rules.json")
        value = JsonConfigLoader.get("risk_rules.json", "some_key", default=[])
    """

    _instance: Optional["JsonConfigLoader"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "JsonConfigLoader":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    obj = super().__new__(cls)
                    obj._cache: dict[str, dict] = {}
                    obj._cache_lock = threading.Lock()
                    cls._instance = obj
        return cls._instance

    # ---- Public class methods (convenience API) ---------------------------

    @classmethod
    def load(cls, file_path: str, use_cache: bool = True) -> dict:
        """Load a JSON config file, returning its parsed content.

        If *use_cache* is True (default) and the file has already been
        loaded, the cached version is returned immediately.

        Relative paths are resolved against *DATA_DIR*.
        """
        instance = cls()
        abs_path = os.path.abspath(
            file_path if os.path.isabs(file_path) else os.path.join(DATA_DIR, file_path)
        )

        if use_cache:
            with instance._cache_lock:
                cached = instance._cache.get(abs_path)
                if cached is not None:
                    return cached

        try:
            with open(abs_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except FileNotFoundError:
            raise FileNotFoundError(f"Config file not found: {abs_path}")
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in config file {abs_path}: {exc}")

        if use_cache:
            with instance._cache_lock:
                instance._cache[abs_path] = data

        return data

    @classmethod
    def reload(cls, file_path: str) -> dict:
        """Force-reload a config file, bypassing and updating the cache."""
        return cls.load(file_path, use_cache=False)

    @classmethod
    def get(cls, file_path: str, key: str, default: Any = None) -> Any:
        """Load a config file and return the value at *key* (dot-separated).

        Supports nested keys via dot notation, e.g. ``"rules.timeout"``.
        """
        data = cls.load(file_path)
        keys = key.split(".")
        current: Any = data
        for k in keys:
            if isinstance(current, dict):
                current = current.get(k)
                if current is None:
                    return default
            else:
                return default
        return current

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the entire in-memory config cache."""
        instance = cls()
        with instance._cache_lock:
            instance._cache.clear()

    # ---- Instance helpers -------------------------------------------------

    def _resolve(self, file_path: str) -> str:
        return os.path.abspath(
            file_path if os.path.isabs(file_path) else os.path.join(DATA_DIR, file_path)
        )


# ---------------------------------------------------------------------------
# LogManager — Singleton logger with rotating file handler
# ---------------------------------------------------------------------------

_LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")


class LogManager:
    """Singleton logger manager providing pre-configured loggers.

    Usage:
        logger = LogManager.get_logger("my_module")
        logger.info("hello")
    """

    _instance: Optional["LogManager"] = None
    _lock = threading.Lock()
    _loggers: dict[str, logging.Logger] = {}

    def __new__(cls) -> "LogManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    obj = super().__new__(cls)
                    obj._initialized = False
                    cls._instance = obj
        return cls._instance

    def _initialize(self) -> None:
        """One-time setup of the log directory and root logger."""
        if self._initialized:
            return
        os.makedirs(_LOG_DIR, exist_ok=True)
        # Root logger with a rotating file handler
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)

        log_file = os.path.join(_LOG_DIR, "log_guard.log")
        handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding="utf-8",
        )
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        # Avoid duplicate handlers on re-initialization
        if not any(isinstance(h, RotatingFileHandler) for h in root_logger.handlers):
            root_logger.addHandler(handler)

        self._initialized = True

    @classmethod
    def get_logger(cls, name: str = "log_guard") -> logging.Logger:
        """Get (or create) a named logger.

        The logger writes to a rotating file under the project *logs/*
        directory.  Callers can attach additional handlers (e.g. a stream
        handler for CLI output) as needed.
        """
        instance = cls()
        instance._initialize()

        if name not in cls._loggers:
            logger = logging.getLogger(name)
            logger.setLevel(logging.DEBUG)
            # Prevent propagation to avoid duplicate messages if the root
            # logger already has handlers attached.
            logger.propagate = True
            cls._loggers[name] = logger

        return cls._loggers[name]

    @classmethod
    def log_parse_failure(
        cls,
        raw_line: str,
        context: Optional[str] = None,
        logger_name: str = "log_guard",
    ) -> None:
        """Log a structured parse-failure record for later analysis."""
        logger = cls.get_logger(logger_name)
        msg = f"PARSE FAILURE: {raw_line!r}"
        if context:
            msg += f" | context: {context}"
        logger.warning(msg)


# ---------------------------------------------------------------------------
# str_util — String cleaning, matching & validation utilities
# ---------------------------------------------------------------------------

IP_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")

# Syslog header pattern: "Mar 15 10:30:25 server " or "<13>Mar 15 10:30:25 "
SYSLOG_HEADER = re.compile(
    r"^(<\d+>\s*)?"
    r"(?:\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\s+\S+\s+)"
    r"|^<\d+>\s*"
)


def clean_special_chars(text: str) -> str:
    """Remove control characters and normalize line endings."""
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.strip()


def clean_syslog_prefix(text: str) -> str:
    """Strip standard syslog headers and common log-level prefixes."""
    # Standard syslog header
    text = SYSLOG_HEADER.sub("", text)
    # Common log-level prefixes
    text = re.sub(
        r"^(INFO|WARN|ERROR|DEBUG|NOTICE)\s*:\s*", "", text, flags=re.IGNORECASE
    )
    # ISO‑8601 timestamp prefixes (e.g. "2024-03-15T10:30:25.123+08:00 hostname ")
    text = re.sub(
        r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+\\.]\S+\s+\S+\s+", "", text
    )
    return text.strip()


def normalize_whitespace(text: str) -> str:
    """Collapse multiple whitespace characters into a single space."""
    return re.sub(r"\s+", " ", text).strip()


def is_gibberish(text: str) -> bool:
    """Return True if *text* is empty, blank, or mostly non‑printable."""
    if not text or not text.strip():
        return True
    stripped = text.strip()
    printable = sum(1 for c in stripped if c.isprintable() or c in "\n\r\t")
    if len(stripped) > 0 and printable / len(stripped) < 0.3:
        return True
    return False


def truncate(text: str, max_length: int = 1000, ellipsis: str = "...") -> str:
    """Truncate *text* to *max_length* characters, breaking at word boundaries."""
    if len(text) <= max_length:
        return text
    return text[:max_length].rsplit(" ", 1)[0] + ellipsis


def extract_ip_from_str(text: str) -> Optional[str]:
    """Return the first IPv4 address found in *text*, or *None*."""
    match = IP_PATTERN.search(text)
    return match.group(0) if match else None
