# ============================================================
# 日志溯源卫士智能体 — 生产镜像
# 多阶段构建: 阶段1 前端构建(可选), 阶段2 后端运行
# ============================================================

# ---------- 阶段1: 前端构建 ----------
FROM node:20-alpine AS frontend-build
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
# 安装含 Rollup 原生模块(已知 npm 可选依赖 bug,见 pitfall #55)
RUN npm install && npm i -D @rollup/rollup-linux-x64-gnu || true
COPY frontend/ ./
RUN npm run build

# ---------- 阶段2: 后端运行 ----------
FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=Asia/Shanghai

WORKDIR /app

# 系统依赖: ChromaDB 需要 libgomp, sentence-transformers 需要 gcc 编译(运行时不需要)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# 先装依赖层(利用缓存)
COPY requirements.txt ./
RUN pip install -r requirements.txt gunicorn==22.0.0

# 复制后端代码
COPY app/ ./app/
COPY common/ ./common/
COPY core/ ./core/
COPY modules/ ./modules/
COPY data/rule_data/ ./data/rule_data/
COPY data/case_data/ ./data/case_data/

# 复制前端构建产物(从阶段1)
COPY --from=frontend-build /build/frontend/dist ./frontend/dist

# 运行时数据目录(挂载卷)
RUN mkdir -p /app/data/chroma_db /app/data/upload_temp /app/logs

# 非 root 运行(企业级安全基线)
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -fs http://127.0.0.1:8000/health || exit 1

EXPOSE 8000

# gunicorn 多 worker + uvicorn worker 类
# 注: 本项目含本地 embedding 模型(sentence-transformers), 每个 worker 独立加载模型
#     内存敏感时设 WEB_CONCURRENCY=1; 纯 API 场景可调大
CMD ["sh", "-c", "gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w ${WEB_CONCURRENCY:-2} -b 0.0.0.0:8000 --timeout 120 --graceful-timeout 30 --access-logfile - --error-logfile -"]
