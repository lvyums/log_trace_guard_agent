"""全局统一异常捕获 — 标准业务异常定义 + 统一返回格式"""

from fastapi import Request
from fastapi.responses import JSONResponse
import time


class AppException(Exception):
    """应用基础异常"""
    def __init__(self, code: int = 400, message: str = "", detail: str = None):
        self.code = code
        self.message = message
        self.detail = detail


class ParamInvalidException(AppException):
    """参数非法"""
    def __init__(self, detail: str = None):
        super().__init__(code=400, message="参数非法", detail=detail)


class LogUnrecognizedException(AppException):
    """日志无法识别"""
    def __init__(self, detail: str = None):
        super().__init__(code=400, message="日志无法识别", detail=detail)


class LogParseFailedException(AppException):
    """日志解析失败"""
    def __init__(self, detail: str = None):
        super().__init__(code=400, message="日志解析失败", detail=detail)


class LLMTimeoutException(AppException):
    """AI 调用异常"""
    def __init__(self, detail: str = None):
        super().__init__(code=503, message="AI 调用异常", detail=detail)


class FileSizeExceededException(AppException):
    """文件超限"""
    def __init__(self, detail: str = None):
        super().__init__(code=413, message="文件大小超限", detail=detail)


def make_response(data=None, msg: str = "success", code: int = 0) -> dict:
    """统一返回结构 — 所有接口强制使用此格式"""
    return {
        "code": code,
        "msg": msg,
        "data": data or {},
        "timestamp": int(time.time() * 1000),
    }


def error_response(msg: str, code: int = 400, data=None) -> dict:
    """统一错误返回"""
    return make_response(data=data, msg=msg, code=code)


async def global_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """全局异常捕获处理器 — 统一返回格式"""
    return JSONResponse(
        status_code=200,  # 业务异常统一 200，业务码在 body 中
        content={
            "code": exc.code,
            "msg": exc.message,
            "data": {"detail": exc.detail} if exc.detail else {},
            "timestamp": int(time.time() * 1000),
        },
    )