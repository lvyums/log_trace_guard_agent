# 日志溯源卫士智能体 v3.2

AI 驱动的安全日志分析与网络安全实训平台，提供日志解析、日志联合审查、规划咨询、故障诊断、脚本生成、合规审计、攻防实训七大模块（模块命名与前端导航一致）。

## 快速启动

### 1. 后端

```bash
# 进入项目目录
cd log_trace_guard_agent

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env，填写 LLM_API_KEY（必填）

# 启动服务（默认端口 8000）
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

启动后访问 `http://localhost:8000` 查看 API 文档。

### 2. 前端

```bash
cd log_trace_guard_agent/frontend

# 安装依赖
npm install

# 开发模式（热更新，端口 5173）
npm run dev
```

访问 `http://localhost:5173`，API 请求自动代理到后端。

### 3. 生产部署

```bash
# 构建前端
cd log_trace_guard_agent/frontend
npm run build

# 启动后端（构建产物由 FastAPI 静态托管）
cd ..
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

访问 `http://localhost:8000` 即可使用。

### 4. CLI 工具

```bash
cd ../log_trace_guard_cli

# 安装依赖
pip install -r requirements.txt

# 运行
python main.py
# 或安装后直接使用
pip install -e .
log-guard
```

CLI 提供日志解析、日志采集、脚本生成、合规审计、日志联合审查、AI 智能对话六大功能，支持离线场景。日志联合审查支持检出 16 种攻击链后一键生成溯源脚本（攻击链→溯源类型自动推断），与 Web 端 `to-trace` 能力对齐。

## 环境变量

| 变量              | 说明                 | 默认值                       |
| ----------------- | -------------------- | ---------------------------- |
| `LLM_API_KEY`     | LLM API 密钥（必填） | -                            |
| `LLM_BASE_URL`    | LLM API 地址         | `https://raytoken.com.cn/v1` |
| `LLM_MODEL_NAME`  | 模型名称             | `deepseek-v4-flash`          |
| `SERVICE_PORT`    | 服务端口             | `8000`                       |
| `EMBEDDING_MODEL` | 嵌入模型             | `BAAI/bge-large-zh-v1.5`     |

完整配置参见 `.env.example`。系统设置面板（前端右上角齿轮图标）支持在线配置 API Key、Splunk、Elasticsearch 连接信息。Splunk/ES 接入详见 `docs/splunk-es配置说明.md`。

## 项目结构

```
log_trace_guard_agent/
├── app/                    # 入口路由层
│   ├── main.py             # FastAPI 主入口
│   ├── settings.py         # 全局配置
│   └── schemas/            # 接口数据模型
├── core/                   # 核心底座层
│   ├── ai_base/            # AI 能力（LLM/RAG/向量库）
│   └── rule_engine/        # 规则引擎
├── modules/                # 业务模块层
│   ├── advisory/           # 规划咨询（v3.1 新增）
│   ├── compliance/         # 合规审计
│   ├── log_collect/        # 采集方案 + 故障诊断（对应前端：规划咨询-采集方案 / 故障诊断）
│   ├── log_correlate/      # 日志联合审查（v3.0 新增）
│   ├── log_parse/          # 日志解析
│   ├── script_gen/         # 脚本生成
│   └── training/           # 实训交互
├── common/                 # 公共工具层
├── data/                   # 配置数据 + 向量库
├── frontend/               # 前端（Vue 3 + Element Plus）
├── tests/                  # 单元测试
└── scripts/dev/            # 联调 mock 服务 + 回归脚本
```

> CLI 工具为同级目录 `../log_trace_guard_cli/`（仓库根，非本目录子目录）。

## API 模块

| 模块           | 路由前缀                        | 功能                             |
| -------------- | ------------------------------- | -------------------------------- |
| 日志解析       | `/api/v1/log-parse`             | 日志识别、解析、风险研判         |
| 日志采集       | `/api/v1/log-collect`           | 设备匹配、采集方案、故障诊断（对应前端：规划咨询-采集方案 + 故障诊断） |
| 脚本生成       | `/api/v1/script-gen`            | 正则生成、ES 查询、Splunk SPL、攻击溯源、脚本优化、连接配置 |
| 合规审计       | `/api/v1/compliance`            | 等保基线生成、合规校验           |
| **规划咨询**   | `/api/v1/advisory`              | 架构推荐、平台选型、指导手册（v3.1 新增） |
| **日志联合审查** | `/api/v1/log-correlate`       | 多源日志攻击链检测（v3.0 新增）  |
| 攻防实训       | `/api/v1/training`              | 攻防场景、任务执行、报告生成     |

> Splunk/ES 接入（搜索执行、连接测试、配置持久化）位于脚本生成模块 `/api/v1/script-gen/splunk/*` 与 `/api/v1/script-gen/es/*`。

## 导航模块

前端 SPA 包含 **7 个导航模块、20 个子页面**：

| 模块           | 子页面数 | 功能描述                           |
| -------------- | -------- | ---------------------------------- |
| 日志解析       | 4        | 识别 → 解析 → 研判 → 批量          |
| **日志联合审查** | 2      | 关联分析、攻击链模式库             |
| **规划咨询**   | 4        | 采集方案、架构推荐、平台选型、指导手册 |
| **故障诊断**   | 1        | 采集故障诊断与修复建议             |
| 脚本生成       | 4        | 正则生成、ES 查询、攻击溯源、脚本优化 |
| 合规审计       | 3        | 合规问答、基线生成、合规自查       |
| 攻防实训       | 2        | 实训场景、实训报告                 |

> 攻防实训模块仅在前端右上角切换为"实训模式"时显示。

## 日志联合审查（v3.0 新增）

支持从多源日志中自动检测 16 种安全攻击链，内置两级引擎：

- **关键词匹配引擎**（零 API 调用）：16 条攻击链规则，中英文关键词，毫秒级响应
- **LLM 语义增强引擎**（可选）：自动降级或强制开启，智能识别复杂攻击链
- **混合模式**：关键词匹配 + LLM 分析合并去重，双向保障

支持的攻击链类型（部分）：
- SSH 暴力破解 → 提权（`ssh_brute_to_privesc`）
- SQL 注入 → 数据外传（`sql_injection_to_data_exfil`）
- C2 通信检测（`c2_beacon_detected`）
- 横向移动（`lateral_movement_via_ssh`）
- 勒索软件准备阶段（`ransomware_staging`）
- DNS 隧道（`dns_tunnel_to_c2`）
