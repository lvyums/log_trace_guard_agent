---
name: run-log-trace-guard-agent
description: Start/stop the log-trace-guard-agent FastAPI server, verify its health, and run smoke tests against all API endpoints. Use when asked to run, build, test, or screenshot the log trace guardian agent.
---

# 日志溯源卫士智能体 (Log Trace Guardian Agent)

FastAPI 后端服务，提供日志解析、风险研判、字段释义等 API。通过 `curl` 或 `driver.sh` 驱动。

所有路径相对于 `log_trace_guard_agent/`。

## 前置条件

- Python 3.10+
- pip 已安装

```bash
pip install -r requirements.txt
pip install httpx          # 测试依赖（可选）
```

## 环境变量

`.env` 文件位于项目根目录，已包含合理默认值。关键变量：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SERVICE_HOST` | `0.0.0.0` | 监听地址 |
| `SERVICE_PORT` | `8000` | 监听端口 |
| `LLM_API_KEY` | `sk-your-key-here` | LLM 密钥（可选，不影响核心功能） |

## 运行（Agent 路径）

### 方式一：冒烟测试驱动（推荐）

```bash
bash .claude/skills/run-log-trace-guard-agent/driver.sh
```

该脚本会自动：启动服务 → 等待就绪 → 冒烟测试核心 API（根路径 / 健康检查 / 日志识别 / 解析 / 研判 / 释义）→ 输出汇总结果 → 清理。

### 方式二：手动控制

**启动：**
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &> /tmp/server.log &
echo $! > /tmp/server.pid
```

**等待就绪：**
```bash
for i in $(seq 1 30); do
  curl -sf http://localhost:8000/health > /dev/null && break
  sleep 1
done
```

**验证：**
```bash
curl http://localhost:8000/
# → {"service":"日志溯源卫士智能体","version":"3.2.0","status":"running"}

curl http://localhost:8000/health
# → {"code":200,"data":{"status":"healthy"},"msg":"success"}
```

**停止：**
```bash
kill "$(cat /tmp/server.pid)" 2>/dev/null
# 或
pkill -f "uvicorn app.main:app"
```

## 运行（人类路径）

```bash
cd log_trace_guard_agent
python -m uvicorn app.main:app --reload
# → 终端阻塞，Ctrl+C 停止
```

## 测试

```bash
cd log_trace_guard_agent
python -m pytest tests/test_rules/ -v
# → 13 passed in 0.14s
```

## API 端点（核心，共 46 个业务端点）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 根路径 / 服务状态（含版本号） |
| GET | `/health` | 健康检查 |
| POST | `/api/v1/log-parse/identify` | 识别日志类型（SSH/Web/WAF/Firewall/DB） |
| POST | `/api/v1/log-parse/parse` | 结构化解析日志 |
| POST | `/api/v1/log-parse/assess` | 异常行为研判 |
| POST | `/api/v1/log-parse/explain` | 字段释义 |
| POST | `/api/v1/log-correlate/correlate` | 多源日志关联分析（攻击链检测） |
| POST | `/api/v1/log-correlate/to-scenario` | 攻击链 → 实训场景 |
| POST | `/api/v1/script-gen/es/search` | ES 搜索执行 |
| POST | `/api/v1/script-gen/splunk/search` | Splunk 搜索执行 |
| POST | `/api/v1/training/dispatch` | 下发实训场景 |

完整端点清单见 `tests/test_api.py` 与 `docs/splunk-es配置说明.md`。

## 常见问题

- **Windows 编码问题**: 终端输出中文乱码时，确保终端支持 UTF-8
- **端口被占用**: 通过 `PORT=8001` 环境变量修改端口
- **LLM 相关错误**: 不影响日志解析核心功能，可忽略