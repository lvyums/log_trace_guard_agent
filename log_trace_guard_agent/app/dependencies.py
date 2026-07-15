"""全局依赖注入 — 请求校验 + 上下文注入"""

import time
from fastapi import Request
from fastapi.responses import JSONResponse

from core.context_manager import ContextManager
from app.settings import settings
from common.logger import LogManager

logger = LogManager.get_logger()


async def validate_request(request: Request):
    """全局请求入参校验依赖 — 所有接口强制接入"""
    # 请求计时
    start_time = time.time()

    # 记录请求日志
    client_ip = request.client.host if request.client else "unknown"
    logger.info(f"[REQ] {request.method} {request.url.path} from {client_ip}")

    # 注入请求开始时间
    request.state.start_time = start_time
    request.state.client_ip = client_ip

    return True


async def log_request_duration(request: Request, response: JSONResponse):
    """响应日志记录 — 记录耗时"""
    duration = int((time.time() - request.state.start_time) * 1000)
    logger.info(
        f"[RESP] {request.method} {request.url.path} "
        f"status={response.status_code} duration={duration}ms"
    )


async def get_context(request: Request) -> ContextManager:
    """请求级 Context 注入"""
    # 尝试从请求体提取用户输入，保留原始输入到上下文
    user_input = ""
    try:
        body = await request.json()
        if isinstance(body, dict):
            # 优先取 log_line，其次取 symptom，兜底取任意文本字段
            user_input = body.get("log_line") or body.get("symptom") or body.get("field_name") or ""
    except Exception:
        pass

    ctx = ContextManager.create(
        user_input=user_input,
        input_type="text",
    )
    return ctx


async def get_settings():
    """全局配置注入"""
    return settings