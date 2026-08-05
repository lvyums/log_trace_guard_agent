# 日志溯源卫士 (Log Trace Guard) v3.2

AI 驱动的安全日志分析与网络安全实训平台，包含 **Web 智能体**（FastAPI + Vue3 SPA）和 **CLI 工具**（log-guard）两个子项目。

## 项目组成

| 子项目 | 目录 | 说明 |
|--------|------|------|
| **Web 智能体** | `log_trace_guard_agent/` | FastAPI 后端 + Vue3 SPA 前端，7 大业务模块、46 个业务 API 端点 |
| **CLI 工具** | `log_trace_guard_cli/` | 终端版，5 大业务模块 + AI 智能对话，可独立安装离线使用 |

## 核心功能

| 模块 | 功能 | 三层架构 |
|------|------|----------|
| **日志解析** | 日志源识别、字段解析、风险评估、批量解析、字段释义 | 规则 → RAG日志基础库 → LLM兜底 |
| **日志采集** | 设备协议匹配、采集方案生成、故障诊断 | 规则 → RAG采集架构库 → LLM故障诊断 |
| **脚本生成** | 正则规则、ES 查询、Splunk SPL、攻击溯源、脚本优化、连接配置 | 规则/模板 → RAG技术脚本库 → LLM生成 |
| **合规审计** | 等保2.0/网安法/数安法问答、合规基线、合规自查 | 规则 → RAG合规审计库 → LLM智能解读 |
| **安全威胁狩猎** | 多源日志关联分析、攻击链检测（16 种模式）、跨模块联动 | 关键词引擎 → RAG模式匹配 → LLM关联推理 |
| **规划咨询** | 架构推荐、平台选型、指导手册 | 规则 → RAG方案库 → LLM方案生成 |
| **攻防实训** | 场景派发、答题评分、SSE 流式讲解、实训报告 | 规则评分 → LLM灰色区间增强 |

## 架构设计

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

### RAG 知识库（5 库）

| 知识库 | 中文名 | 数据来源 |
|--------|--------|----------|
| log_basics | 日志基础库 | log_features, risk_rules |
| compliance | 合规审计库 | compliance_standards, compliance_baselines |
| collection | 采集架构库 | collect_templates, device_protocol, arch_templates |
| scripts | 技术脚本库 | script_gen_*.json |
| cases | 实训案例库 | training_scenarios, standard_answers, fault_kb, correlation_patterns |

### 分层架构

```
app/          FastAPI 路由 + 中间件 + Pydantic 校验 + 管理端点
modules/      7 大业务模块（零耦合，模块间无导入）
core/         LLM 工厂 + 规则引擎 + RAG 知识库 + 上下文管理器
common/       日志 / 文件 / JSON / 结果 等工具
data/         ChromaDB 向量库 + 20 个规则 JSON 文件
frontend/     Vue3 SPA（7 导航模块、20 子页面）
```

## 技术栈

### Web 智能体

| 层级 | 技术 |
|------|------|
| 后端 | FastAPI 0.114 / Uvicorn / Pydantic 2.x |
| AI | OpenAI SDK (DeepSeek V4 Flash) / ChromaDB 1.4.1 / 三级嵌入降级 (BGE → MiniLM → N-gram) |
| 前端 | Vue 3.5 (Vite) / Element Plus 2.9 / TypeScript |
| 数据 | 20 个 JSON 规则文件 → ChromaDB 向量库 |

### CLI 工具

| 层级 | 技术 |
|------|------|
| 运行时 | Python 3.8+ |
| LLM | requests (同步，无 openai 依赖) |
| RAG | 轻量级向量检索（API embeddings + 本地 JSON 缓存） |

## 快速开始

### Web 智能体

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

前端开发模式（热更新，端口 5173）：

```bash
cd log_trace_guard_agent/frontend
npm install
npm run dev
```

### CLI 工具

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

### CLI 命令行用法

```bash
# 基础操作
log-guard --version                             # 查看版本号
log-guard --list-logs                           # 列出系统日志文件
log-guard -f /var/log/auth.log --parse          # 解析日志文件
log-guard -f auth.log -b --assess               # 批量解析 + 风险评估

# AI 问答
log-guard --ask "什么是SQL注入"                   # 非交互式 AI 问答
log-guard --ask "SSH超时原因" --json              # AI 问答（JSON 输出）
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

## Splunk / ES 接入

Web 端与 CLI 端均支持 **实际执行查询**（Splunk SPL 搜索 / ES Query DSL）：

- **Web 端**：系统设置（齿轮图标）→ Splunk / Elasticsearch Tab → 测试连接 / 临时保存（localStorage）/ 保存到 .env（全局生效）
- **CLI 端**：主菜单 → 连接配置，或命令行模式 `--splunk-test` / `--splunk-search` / `--es-test` / `--es-search`
- **联调验证**：仓库内置 mock 服务（`scripts/dev/mock_services.py`，mock Splunk :18089 + mock ES :19200），无真实集群也能验证整条链路

详见 `log_trace_guard_agent/docs/splunk-es配置说明.md`。

## 配置说明

支持三种配置方式（优先级从高到低）：

1. **环境变量**

   ```bash
   export LLM_API_KEY=your_key
   export LLM_BASE_URL=https://raytoken.com.cn/v1
   export LLM_MODEL_NAME=deepseek-v4-flash
   ```
2. **配置文件** `~/.log-guard/config.json`（CLI）或 `.env`（Agent）
3. **默认值**（Agent 内置 `settings.py`，CLI 首次运行配置向导）

所有路径配置基于项目根目录自动计算绝对路径，从任意目录运行均可正确解析。

## 测试

```bash
# Agent 单元测试（145 个）
python -m pytest log_trace_guard_agent/tests/ -v

# CLI 单元测试（243 通过 + 1 跳过）
python -m pytest log_trace_guard_cli/tests/ -v

# Splunk/ES 联调回归（需要先启动 mock 服务）
python log_trace_guard_agent/scripts/dev/mock_services.py &
python log_trace_guard_agent/scripts/dev/test_api_connect.py    # 18 项 API 联调
python log_trace_guard_agent/scripts/dev/test_cli_connect.py    # 16 项 CLI 联调
```

```
测试结果: Agent 145/145 + CLI 243/244（1 跳过，Splunk 连通性需外部服务）全部通过 ✅
```

### CLI 全功能自动测试

`log_trace_guard_cli/tests/test_all_features_capture.py` 自动测试 CLI 全部功能模块并生成终端输出，覆盖 **6 种日志解析器** 和 **14 项功能**。

```bash
cd log_trace_guard_cli

# 运行全功能测试（输出到终端）
python tests/test_all_features_capture.py

# 运行测试并生成 Markdown 展示文档
python tests/test_all_features_capture.py > tests/sample_logs/cli_demo_output.txt
python tests/generate_markdown.py
# → 生成 tests/sample_logs/cli全功能展示.md
```

测试日志文件 `tests/sample_logs/test_all_features.log` 包含 122 行真实日志样本，覆盖 SSH/Web/WAF/Firewall/DB/Generic 六种格式和 P0-P3 四个风险等级。

## 开发指南

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

## 已知限制

1. **BGE 嵌入模型** — 需要 `tf-keras` 包支持 Keras 3 兼容性，否则使用 N-gram 降级
2. **LLM API 配额** — DeepSeek API 偶尔返回 402，自动降级到规则/RAG 兜底
3. **嵌入质量** — N-gram 为非语义向量，检索精度低于 BGE 语义嵌入
4. **Splunk 连通性测试依赖外部服务** — CLI 中该测试标记为 skip，需 Splunk 实例在线
5. **log_correlate 大文件分析性能** — 单文件超 100MB 时 FileCrunch 耗时 >30s，建议分片处理

## 文档索引

| 文档 | 位置 |
|------|------|
| Web 智能体 README | `log_trace_guard_agent/README.md` |
| CLI README | `log_trace_guard_cli/README.md` |
| 前端开发指南 | `log_trace_guard_agent/frontend/README.md` |
| 全局开发规范 | `log_trace_guard_agent/docs/dev_standard.md` |
| 生产部署指南 | `log_trace_guard_agent/docs/生产部署指南.md` |
| Splunk/ES 接入说明 | `log_trace_guard_agent/docs/splunk-es配置说明.md` |
| 功能总结报告 | `log_trace_guard_agent/功能总结报告.md` |
| 测试报告 | `log_trace_guard_agent/测试报告.md` |
| 更新日志 | `CHANGELOG.md` |

## License

MIT
