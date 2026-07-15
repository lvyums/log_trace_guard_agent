"""FastAPI 主入口"""
"""
===== 项目强制开发约束（所有模块开发必须遵守）=====
1. modules业务模块禁止互相import，跨模块数据走core上下文；
2. 工厂必须使用register注册模式，禁止内部硬编码策略实例；
3. 映射表、阈值、故障库禁止写死代码，统一放settings或data/rule_data；
4. 所有入参使用schemas Pydantic校验，未知场景必须兜底；
5. 通用逻辑复用common工具，禁止重复造轮子；
6. 新增场景仅新增策略文件，不修改原有核心代码；
====================================================
"""
import uvicorn
import time
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager

from common.logger import LogManager
from core.ai_base.llm_factory import LLMFactory
from core.rule_engine.regex_rule import RegexRuleEngine
from modules.log_parse.router import router as log_parse_router
from modules.log_collect.router import router as log_collect_router
from modules.script_gen.router import router as script_gen_router
from app.exceptions import AppException, global_exception_handler, make_response
from app.settings import settings
from app.dependencies import validate_request, log_request_duration

logger = LogManager.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("日志溯源卫士智能体 启动中...")
    RegexRuleEngine.load_rules(settings.rule_data_dir)
    logger.info("规则引擎加载完成")
    yield
    await LLMFactory.close_all()
    logger.info("LLM 客户端已关闭")


app = FastAPI(
    title="日志溯源卫士智能体",
    description="AI驱动的日志分析与安全实训平台",
    version="0.1.0",
    lifespan=lifespan,
)

# 全局异常注册
app.add_exception_handler(AppException, global_exception_handler)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """Pydantic 校验异常捕获 — 统一返回格式"""
    errors = exc.errors()
    first_error = errors[0] if errors else {}
    msg = first_error.get("msg", "请求参数校验失败")
    return JSONResponse(
        content=make_response(code=400, msg=msg),
        status_code=200,
    )


@app.middleware("http")
async def global_middleware(request: Request, call_next):
    """全局中间件 — 请求日志 + 耗时记录"""
    start_time = time.time()
    client_ip = request.client.host if request.client else "unknown"
    logger.info(f"[REQ] {request.method} {request.url.path} from {client_ip}")

    try:
        response = await call_next(request)
    except Exception as e:
        duration = int((time.time() - start_time) * 1000)
        logger.error(f"[REQ_ERROR] {request.method} {request.url.path} - {str(e)} [{duration}ms]")
        return JSONResponse(
            content=make_response(code=500, msg="服务器内部错误"),
            status_code=200,
        )

    duration = int((time.time() - start_time) * 1000)
    logger.info(f"[RESP] {request.method} {request.url.path} status={response.status_code} {duration}ms")
    return response


# 路由注册
app.include_router(log_parse_router)
app.include_router(log_collect_router)
app.include_router(script_gen_router)


@app.get("/")
async def root():
    """根路径 — 健康检查"""
    return make_response(data={
        "service": "日志溯源卫士智能体",
        "version": "0.1.0",
        "status": "running",
    })


@app.get("/health")
async def health():
    """健康检查接口"""
    return make_response(data={"status": "healthy"})


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.service_host,
        port=settings.service_port,
        reload=settings.service_reload,
    )