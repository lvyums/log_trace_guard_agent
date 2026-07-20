# 🔍 日志溯源卫士 CLI 智能体 v2.0
**Log Trace Guard Agent — 终端版 | 双模式：菜单操作 + AI 智能对话**

## 一键安装

```bash
pip install -e /path/to/log_trace_guard_cli
# 或
cd log_trace_guard_cli && pip install -e .
```

安装后可直接运行：
```bash
log-guard              # 交互模式
log-guard --ai         # 直接进入 AI 对话模式
log-guard --help       # 查看所有命令
log-guard --version    # 查看版本号
```

> 使用 `pip install -e .`（editable 模式）安装后，代码修改立即生效，无需重新安装。

## 双模式交互

### 模式一：传统菜单（输入数字）
保留所有结构化功能，适合标准化批量操作。

### 模式二：AI 智能对话（直接提问）
```bash
log-guard --ai
```
自由输入任意网络安全、日志运维相关问题：
- 🔍 帮我分析这条日志：sshd: Failed password for root from 192.168.1.100
- 📡 SSH连接超时是什么原因，怎么修复
- 📋 企业日志留存需要满足什么等保要求
- 📝 帮我生成检测SQL注入的正则规则
- 🎓 SQL注入日志怎么溯源攻击链路
- 💡 WAF和防火墙日志的区别是什么

### 全局指令
| 指令 | 说明 |
|------|------|
| `/menu` | 切回传统菜单模式 |
| `/ai` | 进入 AI 对话模式 |
| `/clear` | 清空当前对话上下文 |

## 架构

```
log_guard/
├── cli.py                    # 主入口（argparse + 双模式交互）
├── ai_core/                  # AI 智能核心（全新）
│   ├── llm_client.py         # 同步 LLM 客户端（requests）
│   ├── prompts.py            # 模块级 System Prompt
│   ├── intent_classifier.py  # LLM 意图分类（6类）
│   ├── rag_engine.py         # 轻量 RAG（API嵌入 + 余弦相似度）
│   ├── context.py            # 多轮上下文记忆
│   ├── polisher.py           # 结果润色器
│   ├── orchestrator.py       # 总调度器
│   └── settings.py           # 配置管理（.env / ~/.log-guard/config.json）
├── modules/                  # 5个业务模块（零侵入）
├── core/                     # 日志读取
├── common/                   # 工具类
└── data/rule_data/           # 21个 JSON 规则文件
```

## 核心设计原则

- **业务零侵入**：AI Core 不修改 modules/ 任何代码
- **规则引擎优先**：精准业务操作走原有规则引擎，LLM 只做意图识别 + 结果润色
- **LLM 降级**：API 不可用时自动降级为纯菜单模式
- **轻量 RAG**：废弃 ChromaDB/ONNX，API 嵌入 + 本地 JSON 缓存
- **配置外置**：所有 LLM 参数通过 .env / ~/.log-guard/config.json 配置

## 配置

首次运行会自动引导配置 API Key，也可手动设置：

**方式 A：环境变量**
```bash
export LLM_API_KEY=your_key
export LLM_BASE_URL=https://raytoken.com.cn/v1
export LLM_MODEL_NAME=deepseek-v4-flash
```

**方式 B：.env 文件**
```bash
cp .env.example .env
# 编辑 .env 填入你的 API Key
```

**方式 C：配置文件 `~/.log-guard/config.json`**
```json
{
  "llm_api_key": "your_key",
  "llm_base_url": "https://raytoken.com.cn/v1",
  "llm_model_name": "deepseek-v4-flash"
}
```

## 命令行用法

```bash
# 基础操作
log-guard --version                             # 查看版本号
log-guard --list-logs                           # 列出本机日志
log-guard -f /var/log/auth.log --parse          # 解析日志文件
log-guard -f auth.log -b --assess               # 批量解析 + 风险评估

# AI 问答
log-guard --ask "什么是SQL注入"                   # 非交互式 AI 问答（输出文本）
log-guard --ask "SSH超时原因" --json              # AI 问答（输出 JSON）
log-guard --ai                                   # 进入交互式 AI 对话模式

# 业务功能
log-guard --diagnose "SSH连接超时"                # 故障诊断
log-guard --regex "检测SQL注入"                   # 正则生成
log-guard --es-query "查找登录失败日志"            # ES 查询生成
log-guard --baseline 50                          # 合规基线生成（50 台资产）
log-guard --optimize "(?i)failed" regex          # 脚本优化
log-guard --qa "日志保留要求"                      # 合规问答
log-guard --train basic                          # 实训场景下发

# 输出控制
log-guard -f auth.log -c --json                  # 关联分析（JSON 输出）
```