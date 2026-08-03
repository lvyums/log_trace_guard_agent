"""管理接口 — 配置热加载 + 运行时指标 + 审计日志

企业级运维端点:
- POST /api/v1/admin/reload   重新读取 .env,原地更新 settings 单例(无需重启)
- GET  /api/v1/admin/metrics  运行时结构化指标(请求量/延迟/错误率/LLM 调用统计)

审计日志:
- 全局中间件记录 谁(IP)/何时/调用了什么接口/耗时/状态,写入独立 audit.log
- 原则:记录元数据,不记录请求体(日志内容/密码等敏感数据不进审计日志)

安全说明:企业部署应通过反向代理/Nginx 将此路由限制在内网或加 Basic Auth;
P0 认证体系落地后,此路由将纳入 RBAC 管控。
"""

import time
import json
import threading
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.settings import settings
from app.exceptions import make_response
from common.logger import LogManager
from common.result_util import Result

logger = LogManager.get_logger()

# ── 审计日志(独立文件,轮转) ──
import logging
import os
from logging.handlers import RotatingFileHandler

_audit_logger = logging.getLogger("audit")
_audit_logger.setLevel(logging.INFO)
_logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
os.makedirs(_logs_dir, exist_ok=True)
_audit_handler = RotatingFileHandler(
    os.path.join(_logs_dir, "audit.log"), maxBytes=50 * 1024 * 1024, backupCount=10, encoding="utf-8"
)
_audit_handler.setFormatter(logging.Formatter("%(message)s"))
if not _audit_logger.handlers:
    _audit_logger.addHandler(_audit_handler)

# 审计排除路径(健康检查/静态资源/审计本身,避免噪音)
_AUDIT_EXCLUDE_PREFIXES = ("/health", "/static", "/assets", "/favicon", "/api/v1/admin/metrics")


def audit_log(record: dict) -> None:
    """写入审计日志(JSON 单行)"""
    try:
        _audit_logger.info(json.dumps(record, ensure_ascii=False))
    except Exception:
        pass


def audit_middleware(request: Request, call_next):
    """审计中间件 — 记录 API 调用元数据"""
    start_time = time.monotonic()
    client_ip = request.client.host if request.client else "unknown"
    path = request.url.path

    async def _dispatch():
        nonlocal start_time
        try:
            response = await call_next(request)
        except Exception:
            raise

        duration_ms = int((time.monotonic() - start_time) * 1000)

        # 只审计 API 调用,排除健康检查/静态资源
        if path.startswith("/api/") and not path.startswith(_AUDIT_EXCLUDE_PREFIXES):
            audit_log({
                "ts": datetime.now().isoformat(timespec="seconds"),
                "ip": client_ip,
                "method": request.method,
                "path": path,
                "status": response.status_code,
                "duration_ms": duration_ms,
                "ua": request.headers.get("user-agent", "")[:120],
            })

        return response

    return _dispatch()


router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

# ── 运行时指标存储(进程内,线程安全) ──
_metrics_lock = threading.Lock()
_metrics = {
    "requests_total": 0,
    "requests_by_path": {},          # path -> count
    "requests_by_status": {},        # status -> count
    "total_duration_ms": 0,
    "llm_calls": 0,
    "llm_failures": 0,
    "llm_total_duration_ms": 0,
    "started_at": time.time(),
}


def record_request(path: str, status_code: int, duration_ms: int) -> None:
    """请求指标记录(由全局中间件调用)"""
    with _metrics_lock:
        _metrics["requests_total"] += 1
        _metrics["requests_by_path"][path] = _metrics["requests_by_path"].get(path, 0) + 1
        _metrics["requests_by_status"][str(status_code)] = _metrics["requests_by_status"].get(str(status_code), 0) + 1
        _metrics["total_duration_ms"] += duration_ms


def record_llm_call(success: bool, duration_ms: int) -> None:
    """LLM 调用指标记录(由 LLMFactory 调用)"""
    with _metrics_lock:
        _metrics["llm_calls"] += 1
        if not success:
            _metrics["llm_failures"] += 1
        _metrics["llm_total_duration_ms"] += duration_ms


@router.post("/reload")
async def reload_config(request: Request):
    """热加载 .env 配置 — 无需重启进程"""
    try:
        result = settings.reload_from_env()
        logger.info(f"[ADMIN] 配置热加载完成, {result['changed_count']} 个字段变更, 来源 {request.client.host if request.client else 'unknown'}")
        return Result.ok(
            data={
                "message": "配置已重新加载",
                "changed_count": result["changed_count"],
                "changed": result["changed"],
                "note": "向量库/LLM 客户端等已建立的连接不会热更新, 如需更换模型请重启",
            }
        )
    except Exception as e:
        logger.error(f"[ADMIN] 配置热加载失败: {e}")
        return Result.fail(msg=f"配置热加载失败: {e}")


@router.get("/metrics")
async def get_metrics():
    """运行时指标 — 请求量/延迟/错误率/LLM 调用统计"""
    with _metrics_lock:
        total = _metrics["requests_total"]
        uptime = max(1, int(time.time() - _metrics["started_at"]))
        error_total = sum(
            count for status, count in _metrics["requests_by_status"].items()
            if status.startswith("5")
        )
        llm_success = _metrics["llm_calls"] - _metrics["llm_failures"]
        data = {
            "uptime_seconds": uptime,
            "requests_total": total,
            "requests_per_minute": round(total * 60 / uptime, 2),
            "requests_by_path": dict(sorted(_metrics["requests_by_path"].items(), key=lambda x: -x[1])[:20]),
            "requests_by_status": dict(_metrics["requests_by_status"]),
            "error_rate_5xx": round(error_total / total, 4) if total else 0.0,
            "avg_duration_ms": round(_metrics["total_duration_ms"] / total, 2) if total else 0.0,
            "llm": {
                "calls": _metrics["llm_calls"],
                "failures": _metrics["llm_failures"],
                "success_rate": round(llm_success / _metrics["llm_calls"], 4) if _metrics["llm_calls"] else 0.0,
                "avg_duration_ms": round(_metrics["llm_total_duration_ms"] / _metrics["llm_calls"], 2) if _metrics["llm_calls"] else 0.0,
            },
        }
    return Result.ok(data=data)
