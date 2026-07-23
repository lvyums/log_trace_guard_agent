# 日志溯源卫士智能体

AI 驱动的日志分析与安全实训平台，提供日志解析、合规审计、日志采集、脚本生成、实训交互五大模块。

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

## 环境变量


| 变量              | 说明                 | 默认值                       |
| ----------------- | -------------------- | ---------------------------- |
| `LLM_API_KEY`     | LLM API 密钥（必填） | -                            |
| `LLM_BASE_URL`    | LLM API 地址         | `https://raytoken.com.cn/v1` |
| `LLM_MODEL_NAME`  | 模型名称             | `deepseek-v4-flash`          |
| `SERVICE_PORT`    | 服务端口             | `8000`                       |
| `EMBEDDING_MODEL` | 嵌入模型             | `BAAI/bge-large-zh-v1.5`     |

完整配置参见 `.env.example`。

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
│   ├── log_parse/          # 模块一：日志解析
│   ├── compliance/         # 模块二：合规审计
│   ├── log_collect/        # 模块三：日志采集
│   ├── script_gen/         # 模块四：脚本生成
│   └── training/           # 模块五：实训交互
├── common/                 # 公共工具层
├── data/                   # 配置数据 + 向量库
├── frontend/               # 前端（Vue 3 + Element Plus）
└── tests/                  # 单元测试
```

## API 模块


| 模块     | 路由前缀           | 功能                         |
| -------- | ------------------ | ---------------------------- |
| 日志解析 | `/api/log-parse`   | 日志识别、解析、风险研判     |
| 合规审计 | `/api/compliance`  | 等保基线生成、合规校验       |
| 日志采集 | `/api/log-collect` | 设备匹配、采集方案、故障诊断 |
| 脚本生成 | `/api/script-gen`  | 正则生成、ES 查询、链路追踪  |
| 实训交互 | `/api/training`    | 攻防场景、任务执行、报告生成 |
