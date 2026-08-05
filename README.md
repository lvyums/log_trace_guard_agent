<div align="center">

# 🛡️ 日志溯源卫士 (Log Trace Guard)

**AI 驱动的安全日志分析与网络安全实训平台**

[![Version](https://img.shields.io/badge/version-v3.2.0-blue)]()
[![Backend](https://img.shields.io/badge/FastAPI-0.114-009688)]()
[![Frontend](https://img.shields.io/badge/Vue3-Element_Plus-42b883)]()
[![LLM](https://img.shields.io/badge/LLM-DeepSeek_V4_Flash-4f5d95)]()
[![RAG](https://img.shields.io/badge/RAG-ChromaDB-1.4.1-orange)]()
[![Tests](https://img.shields.io/badge/tests-404_passed-2ea44f)]()

**Web 智能体**（FastAPI + Vue3 SPA）· **CLI 工具**（log-guard）· **Docker 一键部署**

</div>

---

## 📑 目录

- [🚀 项目简介](#-项目简介)
- [✨ 核心功能（全部）](#-核心功能全部)
  - [Web 智能体 7 大模块](#web-智能体-7-大模块)
  - [CLI 智能体](#cli-智能体)
  - [Splunk / ES 集成](#splunk--es-集成)
- [🏗️ 架构设计](#️-架构设计)
  - [三层通用架构](#三层通用架构规则引擎--rag--llm)
  - [RAG 知识库（5 库）](#rag-知识库5-库)
  - [项目目录结构](#项目目录结构)
- [⚡ 快速开始](#-快速开始)
  - [方式一：Docker 部署（推荐）](#方式一docker-部署推荐)
  - [方式二：源码运行](#方式二源码运行)
  - [CLI 安装使用](#cli-安装使用)
- [🧩 全部功能说明](#-全部功能说明)
  - [日志解析](#日志解析模块)
  - [日志采集](#日志采集模块)
  - [脚本生成](#脚本生成模块)
  - [合规审计](#合规审计模块)
  - [日志联合审查 / 安全威胁狩猎](#日志联合审查--安全威胁狩猎模块)
  - [规划咨询](#规划咨询模块)
  - [攻防实训](#攻防实训模块)
  - [CLI 命令行用法速查](#cli-命令行用法速查)
- [🐳 Docker 容器化部署](#-docker-容器化部署)
  - [镜像说明](#镜像说明)
  - [Compose 编排](#compose-编排)
  - [数据持久化](#数据持久化)
  - [运维与排障](#运维与排障)
- [🔧 配置说明](#-配置说明)
- [🧪 测试](#-测试)
- [🛠️ 开发指南](#️-开发指南)
- [📚 文档索引](#-文档索引)
- [⚠️ 已知限制](#️-已知限制)
- [📄 License](#-license)

---

## 🚀 项目简介

日志溯源卫士是一个 **AI 驱动的安全日志分析与网络安全实训平台**，采用 **「规则引擎 → RAG 知识库 → LLM 推理」** 三层通用架构，覆盖从日志采集、解析、研判到攻击链溯源、攻防实训的完整安全运营链路。

| 子项目 | 目录 | 说明 |
|--------|------|------|
| **Web 智能体** | `log_trace_guard_agent/` | FastAPI 后端 + Vue3 SPA 前端，**7 大业务模块、46 个业务 API 端点、20 个子页面** |
| **CLI 工具** | `log_trace_guard_cli/` | 终端版，**5 大业务模块 + AI 智能对话**，可独立安装离线使用 |

**核心亮点：**

- 🧠 **三层通用架构**：规则引擎（零依赖、可穷举测试）→ RAG 知识库（5 分片）→ LLM 推理（DeepSeek），三级降级容错
- 🔗 **16 种攻击链检测**：SSH 爆破提权、SQL 注入、横向移动、数据窃取、C2、勒索、DNS 隧道、供应链等
- 🎯 **攻击链 → 实训场景闭环**：检测到攻击链后一键生成专属实战场景（LLM 动态定制，失败自动降级）
- 🔌 **Splunk / ES 实际执行**：SPL 搜索、Query DSL 执行、连接测试、配置持久化（Web + CLI 双端）
- 📦 **Docker 一键部署**：多阶段构建、非 root 运行、健康检查、资源限制、数据卷持久化

---

## ✨ 核心功能（全部）

### Web 智能体 7 大模块

| # | 模块 | 功能 | 三层架构 | 端点 |
|---|------|------|----------|------|
| 1 | **日志解析** | 日志源识别、结构化字段解析、风险研判（P0-P3）、字段释义问答、批量解析 | 规则 → RAG日志基础库 → LLM兜底 | 9 |
| 2 | **日志采集** | 设备协议匹配、采集方案生成、分层架构推荐、故障智能排错 | 规则 → RAG采集架构库 → LLM故障诊断 | 5 |
| 3 | **脚本生成** | 正则规则、ES 查询、Splunk SPL、攻击溯源、脚本优化、连接配置 | 规则/模板 → RAG技术脚本库 → LLM生成 | 13 |
| 4 | **合规审计** | 等保2.0/网安法/数安法问答、合规基线生成、合规自查整改 | 规则 → RAG合规审计库 → LLM智能解读 | 4 |
| 5 | **安全威胁狩猎** | 多源日志关联分析、16 种攻击链检测、大文件分片、攻击链转实训 | 关键词引擎 → RAG模式匹配 → LLM关联推理 | 8 |
| 6 | **规划咨询** | 采集架构推荐、日志平台选型、定制指导手册 | 规则 → RAG方案库 → LLM方案生成 | 3 |
| 7 | **攻防实训** | 场景派发、答题双维度评分、SSE 流式讲解、实训报告 | 规则评分 → LLM灰色区间增强 | 4 |

> 📌 每个模块都有独立子页面（共 20 个），支持**运维 / 实训双模式**切换与跨模块联动。

### CLI 智能体

- **双模式交互**：传统菜单（6 大业务模块：解析/采集/脚本/合规/联合审查/AI对话 + 文件选择 + 退出）+ AI 智能对话（6 类意图识别）
- **脚本生成增强**：溯源报告导出（Markdown/JSON）、ES 查询模板管理、溯源→监控规则闭环、Splunk SPL 一键执行
- **命令行模式**：`--splunk-search` / `--es-search` 等，退出码契约（0/1/2），支持 `--json`，适合脚本集成

### Splunk / ES 集成

- **Web 端**：系统设置 → Splunk / Elasticsearch 面板 → 测试连接 / 临时保存（localStorage）/ 保存到 .env（全局持久化）
- **CLI 端**：主菜单连接配置 + 命令行模式 4 个命令
- **联调验证**：内置 mock 服务（`scripts/dev/mock_services.py`，mock Splunk :18089 + ES :19200），无真实集群也能验证全链路

---

## 🏗️ 架构设计

### 三层通用架构（规则引擎 + RAG + LLM）

```
用户请求
  │
  ▼
┌──────────────┐    匹配成功     ┌──────────────┐
│  规则引擎     │ ──────────────▶ │  直接返回     │
│  (JSON/正则)  │                └──────────────┘
└──────┬───────┘
       │ 匹配不足
       ▼
┌──────────────┐    检索到知识    ┌──────────────┐
│  RAG 知识库   │ ──────────────▶ │  补充返回     │
│  (ChromaDB)  │                └──────────────┘
└──────┬───────┘
       │ 无知识 / 需深度解读
       ▼
┌──────────────┐    生成回答      ┌──────────────┐
│  LLM 推理     │ ──────────────▶ │  智能返回     │
│  (DeepSeek)  │                └──────────────┘
```

**降级策略**：LLM 失败 → RAG 兜底 → 规则降级；动态场景失败 → fallback → 传统场景。所有 LLM 调用经统一接口 `BaseLLMClient.chat()`，返回 `{success, content, error}`。

### RAG 知识库（5 库）

| 知识库 | 中文名 | 数据来源 | 服务模块 |
|--------|--------|----------|----------|
| `log_basics` | 日志基础库 | log_features, risk_rules | 日志解析 |
| `compliance` | 合规审计库 | compliance_standards, compliance_baselines | 合规审计 |
| `collection` | 采集架构库 | collect_templates, device_protocol, arch_templates | 日志采集 / 规划咨询 |
| `scripts` | 技术脚本库 | script_gen_*.json | 脚本生成 |
| `cases` | 实训案例库 | training_scenarios, standard_answers, fault_kb, correlation_patterns | 威胁狩猎 / 攻防实训 |

向量嵌入三级降级：**BGE**（1024 维）→ **MiniLM**（384 维）→ **N-gram**（128 维，当前降级态）。

### 项目目录结构

```
agent/                                  # 仓库根
├── README.md                           # 本文档
├── CHANGELOG.md                        # 更新日志
├── 日志溯源卫士-源码级完整项目说明.md      # 源码级项目说明 (v3.2.0)
├── 日志溯源卫士智能体-详细设计.md         # 详细设计文档 (v3.2.0)
│
├── log_trace_guard_agent/              # ── Web 智能体 ──
│   ├── Dockerfile                      # 生产镜像（多阶段构建）
│   ├── docker-compose.yml              # Compose 编排
│   ├── .env.example                    # 环境变量模板
│   ├── app/                            # FastAPI 路由 + Pydantic 校验 + 管理端点
│   ├── modules/                        # 7 大业务模块（零耦合）
│   ├── core/                           # LLM 工厂 + 规则引擎 + RAG + 上下文管理器
│   ├── common/                         # 日志 / 文件 / JSON / Splunk / ES 客户端
│   ├── data/                           # ChromaDB 向量库 + 20 个规则 JSON
│   ├── frontend/                       # Vue3 SPA（7 导航模块、20 子页面）
│   ├── scripts/dev/                    # mock 服务 + 联调回归脚本
│   ├── tests/                          # 161 个测试
│   └── docs/                           # 部署 / 开发规范 / 配置说明
│
└── log_trace_guard_cli/                # ── CLI 智能体 ──
    ├── log_guard/                      # cli.py + ai_core + 5 业务模块
    ├── tests/                          # 243 测试（+1 跳过）
    └── setup.py / pyproject.toml       # 可独立安装
```

---

## ⚡ 快速开始

### 方式一：Docker 部署（推荐）

前置要求：Docker 20.10+ 与 Docker Compose v2。

```bash
cd log_trace_guard_agent

# 1. 配置环境变量
cp .env.example .env
# 编辑 .env，必填 LLM_API_KEY

# 2. 构建并启动（自动编译前端 + 后端，首次约 5-10 分钟）
docker compose up -d --build

# 3. 验证
curl http://localhost:8000/health
# → {"code":0,"msg":"success","data":{"status":"healthy"},"timestamp":...}

# 4. 访问
# http://localhost:8000   （前端页面 + API 同一端口）
```

> 💡 无需单独启动前端 — 镜像多阶段构建已把 Vue3 SPA 编译进后端静态目录。

### 方式二：源码运行

**后端（Web 智能体）：**

```bash
cd log_trace_guard_agent

# 安装依赖
pip install -r requirements.txt

# 配置 LLM（可选，有默认值）
cp .env.example .env
# 编辑 .env 填入 LLM_API_KEY

# 启动服务（首次启动自动导入知识库数据）
python -m app.main
# 访问 http://localhost:8000
```

**前端开发模式（热更新，端口 5173）：**

```bash
cd log_trace_guard_agent/frontend
npm install
npm run dev
```

### CLI 安装使用

```bash
cd log_trace_guard_cli

# 安装（推荐 editable 模式）
pip install -e .

# 运行
log-guard              # 交互式菜单模式
log-guard --ai         # AI 对话模式
log-guard --help       # 查看所有命令
```

**配置 LLM（三选一）：**

```bash
# 方式 A：环境变量
export LLM_API_KEY=your_key_here

# 方式 B：.env 文件
cp .env.example .env

# 方式 C：配置向导（首次启动自动触发）
log-guard
```

---

## 🧩 全部功能说明

### 日志解析模块

| 能力 | 端点 | 说明 |
|------|------|------|
| 日志识别 | `POST /api/v1/log-parse/identify` | 自动识别设备类型（ssh/web/firewall/waf/db/traffic） |
| 结构化解析 | `POST /api/v1/log-parse/parse` | 提取 src_ip/dst_ip/user/action/risk 等标准字段 |
| 风险研判 | `POST /api/v1/log-parse/assess` | P0-P3 五级风险 + 处置建议 |
| 字段释义 | `POST /explain` `/explain/batch` | RAG 检索 + LLM 讲解字段含义 |
| 批量解析 | `POST /parse/batch` `/parse/batch-file` `/upload` | 批量文件解析（单文件 ≤10MB） |

### 日志采集模块

| 能力 | 端点 | 说明 |
|------|------|------|
| 设备匹配 | `POST /api/v1/log-collect/match` | 按厂商/型号/协议匹配采集模板 |
| 采集方案 | `POST /plan` `/plan/batch` | 输出标准化采集配置（syslog/SNMP/API） |
| 故障诊断 | `POST /fault/diagnose` `GET /fault/list` | 关键词匹配故障库，输出原因 + 修复步骤 |

### 脚本生成模块

| 能力 | 端点 | 说明 |
|------|------|------|
| 正则生成 | `POST /regex` `/regex/batch` | LLM 生成 + 一键对日志测试命中率 |
| ES 查询 | `POST /es-query` `/es-query/batch` | 生成 Query DSL |
| ES 执行 | `POST /es/search` | DSL 校验 + 实际执行（返回集群名/版本） |
| 攻击溯源 | `POST /trace` | 按攻击类型生成溯源检索脚本 |
| 脚本优化 | `POST /optimize` | LLM 评分 + 优化建议 |
| Splunk SPL | `POST /splunk/search` `/splunk/open-url` | 5 场景模板生成 SPL + REST 执行 + Web UI 跳转 |
| 连接管理 | `POST /splunk/test` `/splunk/config` `/es/test` `/es/config` | 测试连接 + 配置持久化到 .env |

### 合规审计模块

| 能力 | 端点 | 说明 |
|------|------|------|
| 合规问答 | `POST /api/v1/compliance/qa` | 等保2.0 / 网安法 / 数安法，RAG 引用条款 |
| 基线生成 | `POST /baseline` | 按资产信息生成合规基线报告（可下载 Markdown） |
| 合规自查 | `POST /check` `/check/batch` | 配置项逐条比对 → 满足/缺口 + 整改建议 |

### 日志联合审查 / 安全威胁狩猎模块

| 能力 | 端点 | 说明 |
|------|------|------|
| 关联分析 | `POST /api/v1/log-correlate/correlate` | 关键词+LLM 双引擎，检测 **16 种攻击链** |
| 大文件分片 | `POST /file-crunch` `/upload` | 超大日志分片分析 |
| 攻击链→溯源脚本 | `POST /to-trace` | 一键生成溯源脚本 |
| 攻击链→实训场景 | `POST /to-scenario` | **动态生成专属实战场景**（LLM 失败降级 fallback） |
| 模式列表 | `GET /patterns` | 查看全部可检测攻击链 |

**16 种攻击链模式**：SSH暴力破解后提权、暴力破解、SQL注入、Web扫描到利用、入口入侵到横向移动、权限提升、数据窃取、C2通信、勒索软件、内网侦察、Web攻击到数据窃取、DNS隧道、供应链攻击、内部威胁、WAF告警到攻击、认证失败关联。

### 规划咨询模块

| 能力 | 端点 | 说明 |
|------|------|------|
| 架构推荐 | `POST /api/v1/advisory/architecture/recommend` | 按企业规模推荐采集架构 |
| 平台选型 | `POST /platform/choose` | 多平台多维度打分对比 |
| 指导手册 | `POST /guide/generate` | 按场景生成定制化指导手册 |

### 攻防实训模块

| 能力 | 端点 | 说明 |
|------|------|------|
| 场景派发 | `POST /api/v1/training/dispatch` | 12 个预置场景 + 动态场景（DYN_） |
| 答案提交 | `POST /submit` | 关键词规则 + LLM 语义双维度评分 |
| 流式讲解 | `POST /analyze-stream` | SSE 流式返回分析过程 |
| 实训报告 | `POST /report` | 按场景/学员聚合统计报告 |

### CLI 命令行用法速查

```bash
# 基础操作
log-guard --version                             # 查看版本号
log-guard --list-logs                           # 列出系统日志文件
log-guard -f /var/log/auth.log --parse          # 解析日志文件
log-guard -f auth.log -b --assess              # 批量解析 + 风险评估

# AI 问答
log-guard --ask "什么是SQL注入"                   # 非交互式 AI 问答
log-guard --ask "SSH超时原因" --json             # AI 问答（JSON 输出）
log-guard --ai                                   # 进入交互式 AI 对话模式

# 业务功能
log-guard --diagnose "SSH connection timeout"    # 故障诊断
log-guard --regex "detect SQL injection"         # 生成正则规则
log-guard --es-query "查找登录失败日志"            # 生成 ES 查询
log-guard --baseline 50                          # 合规基线生成（50 台资产）
log-guard --optimize "(?i)failed" regex          # 脚本优化
log-guard --qa "日志留存要求"                      # 合规问答
log-guard -f auth.log -c                         # 跨源日志关联分析

# Splunk / ES 连接测试与搜索（退出码 0=成功 / 1=失败 / 2=DSL 非法）
log-guard --splunk-test --json                   # 测试 Splunk 连接
log-guard --splunk-search 'search index=* | head 5' --json   # 执行 SPL 搜索
log-guard --es-test --json                       # 测试 ES 连接（返回集群名/版本）
log-guard --es-search '{"query":{"match_all":{}},"size":5}' --json   # 执行 ES 查询

# 输出控制
log-guard -f auth.log -c --json                  # 关联分析（JSON 输出）
```

---

## 🐳 Docker 容器化部署

### 镜像说明

仓库内置生产级 `Dockerfile`（`log_trace_guard_agent/`），**多阶段构建**：

```
阶段 1: node:20-alpine   → 编译 Vue3 前端（npm run build）
阶段 2: python:3.10-slim → 安装 Python 依赖 + 复制后端代码 + 前端产物
```

**镜像特性（企业级安全基线）：**

| 特性 | 说明 |
|------|------|
| 🛡️ 非 root 运行 | `USER appuser`（uid 1000） |
| 🩺 健康检查 | `HEALTHCHECK` 每 30s 探测 `/health` |
| 🔄 多 worker | gunicorn + uvicorn worker（`WEB_CONCURRENCY` 可调） |
| 📦 分层缓存 | 依赖层独立 COPY，构建复用缓存 |
| 🌏 时区 | `TZ=Asia/Shanghai` |

### Compose 编排

仓库内置 `docker-compose.yml`，开箱即用：

```bash
cd log_trace_guard_agent

# 首次部署
cp .env.example .env      # 填 LLM_API_KEY
docker compose up -d --build

# 后续更新
git pull
docker compose up -d --build --no-deps

# 查看状态
docker compose ps
docker compose logs -f log-guard
```

**编排要点（已内置）：**

| 项 | 配置 |
|----|------|
| 端口 | `8000:8000`（前后端一体） |
| 重启策略 | `restart: unless-stopped` |
| 资源限制 | 内存上限 4G / CPU 4.0（`deploy.resources`） |
| 日志轮转 | json-file，单文件 50MB × 5 个 |
| Worker 数 | 默认 1（含本地 embedding 模型，内存敏感） |

### 数据持久化

| 卷/目录 | 挂载点 | 说明 |
|---------|--------|------|
| `./data/chroma_db` | `/app/data/chroma_db` | **核心数据** — 向量知识库（必须备份） |
| `./data/upload_temp` | `/app/data/upload_temp` | 上传临时文件 |
| `./logs` | `/app/logs` | 应用日志 |

> ⚠️ 规则 JSON（`data/rule_data/`）在镜像内固化，改动需重新构建；向量库与日志走宿主目录持久化。

### 运维与排障

```bash
# 健康检查
curl http://localhost:8000/health
# → {"code":0,"msg":"success","data":{"status":"healthy"},"timestamp":...}

# 服务信息（容器内根路径返回前端页面；无构建产物时返回 JSON）
curl http://localhost:8000/
# → {"code":0,"msg":"success","data":{"service":"日志溯源卫士智能体","version":"3.2.0","status":"running"},"timestamp":...}

# 重置向量库（知识库损坏/升级时）
docker compose down
rm -rf data/chroma_db
docker compose up -d          # 首次启动自动重新导入

# 内存不足时限制 worker
WEB_CONCURRENCY=1 docker compose up -d

# 修改端口
# 编辑 docker-compose.yml 的 ports: "9000:8000"
```

---

## 🔧 配置说明

支持三种配置方式（优先级从高到低）：

1. **环境变量**

   ```bash
   export LLM_API_KEY=your_key
   export LLM_BASE_URL=https://raytoken.com.cn/v1
   export LLM_MODEL_NAME=deepseek-v4-flash
   ```

2. **配置文件** `~/.log-guard/config.json`（CLI）或 `.env`（Agent）

3. **默认值**（Agent 内置 `settings.py`，CLI 首次运行配置向导）

**关键配置项（`.env.example`）：**

| 分组 | 变量 | 默认值 |
|------|------|--------|
| 服务 | `SERVICE_HOST` / `SERVICE_PORT` | `0.0.0.0` / `8000` |
| LLM | `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL_NAME` | 必填 / `https://raytoken.com.cn/v1` / `deepseek-v4-flash` |
| 向量 | `EMBEDDING_MODEL` / `RERANKER_MODEL` | `BAAI/bge-large-zh-v1.5` / `BAAI/bge-reranker-large` |
| 上传 | `MAX_UPLOAD_SIZE_MB` / `ALLOWED_EXTENSIONS` | `10` / `[".txt",".csv",".log"]` |
| Splunk | `SPLUNK_BASE_URL` / `SPLUNK_AUTH_TOKEN` / `SPLUNK_VERIFY_SSL` | 空 / 空 / `true` |
| ES | `ES_BASE_URL` / `ES_USERNAME` / `ES_PASSWORD` | 空 / 空 / 空 |

所有路径配置基于项目根目录自动计算绝对路径，从任意目录运行均可正确解析。

---

## 🧪 测试

```bash
# Agent 单元测试（161 个）
python -m pytest log_trace_guard_agent/tests/ -v

# CLI 单元测试（243 通过 + 1 跳过）
python -m pytest log_trace_guard_cli/tests/ -v

# Splunk/ES 联调回归（需要先启动 mock 服务）
python log_trace_guard_agent/scripts/dev/mock_services.py &
python log_trace_guard_agent/scripts/dev/test_api_connect.py    # 18 项 API 联调
python log_trace_guard_agent/scripts/dev/test_cli_connect.py    # 16 项 CLI 联调
```

```
测试结果: Agent 161/161 + CLI 243/244（1 跳过，Splunk 连通性需外部服务）全部通过 ✅
```

**测试覆盖亮点**：

- `tests/test_rules/test_to_scenario.py`（16 用例）— 攻击链→实训场景全链路（fallback 降级 / LLM 生成 / 动态注入 / API 集成）
- CLI 全功能自动测试：`tests/test_all_features_capture.py` 覆盖 6 种解析器 + 14 项功能，122 行真实日志样本

---

## 🛠️ 开发指南

### 添加新日志解析器

继承 `BaseParser`，实现 `can_parse()` 和 `parse_fields()`，调用 `LogParserFactory.register()` 注册即可。

### 添加新知识库

1. 在 `core/ai_base/kb_ingest.py` 的 `KB_FILE_MAP` 中添加映射
2. 在 `core/ai_base/rag_factory.py` 的 `KB_REGISTRY` 中注册
3. 放置 JSON 数据文件到 `data/rule_data/`
4. 重启服务自动导入

### CLI 设计原则

- **业务零侵入**：AI Core 不修改 `modules/` 代码
- **规则引擎优先**：精确操作走规则引擎，LLM 仅做意图识别 + 结果润色
- **LLM 优雅降级**：API 不可用时自动回退到纯菜单模式

### 模块开发规范

完整开发规范见 `log_trace_guard_agent/docs/dev_standard.md`（模块架构、RAG API、三层落地、测试要求）。

---

## 📚 文档索引

| 文档 | 位置 | 内容 |
|------|------|------|
| **源码级完整项目说明** | `日志溯源卫士-源码级完整项目说明.md` | 全部代码文件级详解（v3.2.0） |
| **详细设计文档** | `日志溯源卫士智能体-详细设计.md` | 架构/模块/闭环设计（v3.2.0） |
| Web 智能体 README | `log_trace_guard_agent/README.md` | Agent 模块/API/前端说明 |
| CLI README | `log_trace_guard_cli/README.md` | CLI 安装/菜单/命令 |
| 前端开发指南 | `log_trace_guard_agent/frontend/README.md` | Vue3 组件/页面开发 |
| 全局开发规范 | `log_trace_guard_agent/docs/dev_standard.md` | 模块架构/RAG/三层落地 |
| 生产部署指南 | `log_trace_guard_agent/docs/生产部署指南.md` | Docker/systemd/环境变量 |
| Splunk/ES 接入说明 | `log_trace_guard_agent/docs/splunk-es配置说明.md` | 双端接入/联调验证 |
| 功能总结报告 | `log_trace_guard_agent/功能总结报告.md` | 功能验收清单 |
| 测试报告 | `log_trace_guard_agent/测试报告.md` | 测试分布/性能/已知限制 |
| 更新日志 | `CHANGELOG.md` | 版本历史 |

---

## ⚠️ 已知限制

1. **BGE 嵌入模型** — 需要 `tf-keras` 包支持 Keras 3 兼容性，否则使用 N-gram 降级
2. **LLM API 配额** — DeepSeek API 偶尔返回 402，自动降级到规则/RAG 兜底
3. **嵌入质量** — N-gram 为非语义向量，检索精度低于 BGE 语义嵌入
4. **Splunk 连通性测试依赖外部服务** — CLI 中该测试标记为 skip，需 Splunk 实例在线
5. **log_correlate 大文件分析性能** — 单文件超 100MB 时 FileCrunch 耗时 >30s，建议分片处理
6. **「保存到 .env」依赖写权限** — Docker 容器内写权限可能丢失，生产建议环境变量注入

---

## 📄 License

MIT

---

<div align="center">

**日志溯源卫士 Log Trace Guard v3.2.0** · 规则引擎 · RAG 知识库 · LLM 推理 · 攻防实训

</div>
