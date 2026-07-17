# 日志溯源卫士 (Log Trace Guard)

AI 驱动的安全日志分析与网络安全实训平台，包含 **Web 智能体** 和 **CLI 工具** 两个子项目。

## 核心功能

| 模块 | 功能 | 说明 |
|------|------|------|
| **日志解析** | 日志源识别、字段解析、风险评估、批量解析 | 支持 SSH / Web / WAF / 防火墙 / 数据库 5 类解析器 |
| **日志采集** | 设备协议匹配、采集方案生成、故障诊断、架构推荐 | 支持 syslog / SNMP / agent 三种采集方式 |
| **脚本生成** | 正则检测规则、ES 查询语句、攻击链追踪脚本 | 覆盖规则生成、平台推荐、脚本优化 |
| **合规审计** | 等保 2.0 / 网安法 / 数安法问答、合规基线、差距分析 | 内置合规知识库，支持差距分析与整改建议 |
| **攻防实训** | 场景派发、答题评分、报告生成 | 支持运维/实训双模式切换 |

## 项目结构

```
log_trace_guard_agent/     # Web 智能体 (FastAPI + Vue3)
├── app/                   # FastAPI 后端
│   ├── main.py            # 入口
│   ├── settings.py        # 配置
│   ├── modules/           # 5 大业务模块（零耦合）
│   ├── core/              # AI 工厂 + 规则引擎 + RAG
│   ├── common/            # 工具函数
│   └── data/              # 知识库 + 规则数据
├── static/                # Vue3 前端 SPA
│   ├── index.html
│   ├── js/                # 组件 + 路由 + API
│   └── css/               # 主题 + 响应式
└── requirements.txt

log_trace_guard_cli/       # CLI 工具 (纯 Python)
├── log_guard/
│   ├── cli.py             # 主入口
│   ├── ai_core/           # AI 智能核心（意图分类 + RAG + 编排）
│   ├── modules/           # 5 大业务模块
│   ├── core/              # 日志读取
│   └── data/              # 规则数据
├── main.py
└── pyproject.toml
```

## 技术栈

### Web 智能体

| 层级 | 技术 |
|------|------|
| 后端 | FastAPI 0.114 / Uvicorn / Pydantic 2.x |
| AI | OpenAI SDK (DeepSeek-v4-flash) / ChromaDB / sentence-transformers (BAAI/bge-large-zh-v1.5) |
| 前端 | Vue 3.5 (CDN) / Element Plus 2.9 / 原生 CSS（明暗主题 + 响应式） |

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

# 启动服务
python -m app.main
# 访问 http://localhost:8000
```

### CLI 工具

```bash
cd log_trace_guard_cli

# 安装（推荐）
pip install -e .

# 运行
log-guard              # 交互式菜单模式
log-guard --ai         # AI 对话模式
log-guard --help       # 查看所有命令
```

首次运行会自动检测 API Key 并引导配置。

### CLI 命令行用法

```bash
log-guard --list-logs                         # 列出系统日志文件
log-guard -f /var/log/auth.log --parse        # 解析日志文件
log-guard -f auth.log -b --assess             # 批量解析 + 风险评估
log-guard --diagnose "SSH connection timeout" # 故障诊断
log-guard --regex "detect SQL injection"      # 生成正则规则
log-guard --qa "日志留存要求"                   # 合规问答
log-guard --train basic                       # 派发训练场景
```

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

## 架构设计

### AI 三层处理流水线

```
用户输入 → 规则引擎（精确匹配）→ RAG 知识库（语义检索）→ LLM（兜底推理）→ 结果润色 → 输出
```

### Web 智能体 5 层架构

```
app/          FastAPI 路由 + 中间件 + Pydantic 校验
modules/      5 大业务模块（零耦合，模块间无导入）
core/         LLM 工厂 + 规则引擎 + RAG 引擎 + 上下文管理器
common/       日志 / 文件 / IP / JSON / 结果 等工具
data/         ChromaDB 向量库 + 20+ 规则 JSON 文件
```

### CLI 双模式架构

```
菜单模式        编号菜单导航，结构化输入，JSON 输出（可管道化）
AI 对话模式     自然语言 → 意图分类（6 类）→ RAG 检索 → 模块执行 → 响应润色
```

## 开发指南

### 添加新日志解析器

继承 `BaseParser`，实现 `can_parse()` 和 `parse_fields()`，调用 `LogParserFactory.register()` 注册即可，无需修改已有代码。

### CLI 设计原则

- **业务零侵入**：AI Core 不修改 `modules/` 代码
- **规则引擎优先**：精确操作走规则引擎，LLM 仅做意图识别 + 结果润色
- **LLM 优雅降级**：API 不可用时自动回退到纯菜单模式

## License

MIT
