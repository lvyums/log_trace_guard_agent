# 🔍 日志溯源卫士 CLI 智能体 v3.0
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
保留所有结构化功能，适合标准化批量操作。主菜单 7 项：
1. 选择日志文件
2. 日志解析
3. 日志采集
4. **脚本生成** — 正则/ES查询/Splunk SPL/攻击溯源/脚本优化/连接配置
5. 合规审计
6. 联合日志审查
7. AI 智能对话

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
├── ai_core/                  # AI 智能核心
│   ├── llm_client.py         # 同步 LLM 客户端（requests）
│   ├── prompts.py            # 模块级 System Prompt
│   ├── intent_classifier.py  # LLM 意图分类（6类）
│   ├── rag_engine.py         # 轻量 RAG（API嵌入 + 余弦相似度）
│   ├── context.py            # 多轮上下文记忆
│   ├── polisher.py           # 结果润色器
│   ├── orchestrator.py       # 总调度器
│   └── settings.py           # 配置管理（.env / ~/.log-guard/config.json）
├── modules/                  # 5个业务模块（零侵入）
│   ├── log_parse.py          # 日志解析
│   ├── log_collect.py        # 日志采集
│   ├── script_gen.py         # 脚本生成（正则/ES/Splunk/溯源/优化）
│   ├── compliance.py         # 合规审计
│   └── log_correlate.py      # 联合日志审查
├── core/                     # 日志读取
├── common/                   # 工具类
└── data/rule_data/           # 16个 JSON 规则文件
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

### ES / Splunk 连接配置

ES 和 Splunk 集群的连接配置也存储在 `~/.log-guard/config.json`，通过菜单「连接配置」交互配置：

```json
{
  "llm_api_key": "your_key",
  "es": {
    "host": "192.168.1.100",
    "port": 9200,
    "scheme": "http",
    "user": "",
    "password": ""
  },
  "splunk": {
    "host": "192.168.1.100",
    "port": 8089,
    "scheme": "https",
    "user": "",
    "password": ""
  }
}
```

## ✨ 脚本生成增强（v3.0 新功能）

脚本生成子菜单扩展为 **6 项功能**，新增「Splunk SPL 生成」，连接配置合并为「ES / Splunk 双入口」：

### 1. 正则规则生成 → 一键测试
输入攻防场景描述 → LLM 生成正则规则 → 可选对日志文件执行匹配测试，展示命中率 + 样本。

### 2. ES 查询生成 → 一键执行 + 模板保存
输入检索场景 → 生成 ES Query DSL → 可选连接 ES 集群执行查询 → 可选保存为命名模板。

**模板管理**：内置 SSH爆破检测、SQL注入检测两个预置模板。可在子菜单查看、加载执行、删除模板。模板存储在 `~/.log-guard/es_templates.json`。

### 3. Splunk SPL 生成 → 一键执行
输入场景描述（如 SSH爆破攻击、SQL注入、Web攻击）→ 自动匹配 5 种场景模板 → 生成 SPL 语句 → 可选连接 Splunk REST API 执行查询。

支持中文场景名智能匹配（SSH爆破→ssh_brute模板，SQL注入→sql_injection模板）：
```bash
# 生成的 SPL 示例
index=* sourcetype=ssh* "Failed password" OR "Invalid user"
  | stats count by src_ip | where count > 5 | sort -count
```

### 4. 攻击溯源 → 报告导出 + 监控规则闭环
加载日志文件 → 输入/自动识别攻击类型 → 分析攻击链（6阶段） → 溯源完成后新增两个可选步骤：

- **📄 导出报告**：Markdown/JSON 格式，保存至 `~/.log-guard/reports/`，含攻击链分段 + 时间线表格
- **🔄 生成监控规则**：自动提取 keywords + IPs → 同时生成 ES Query DSL + 正则检测规则 → 可一键保存为 ES 模板

> **闭环意义**：分析一次攻击 → 生成持续监控规则，溯源不再是"死胡同"

### 5. 脚本优化
输入现有正则/ES 查询脚本，LLM 评分 + 优化建议。

### 6. 连接配置
统一管理 ES 集群和 Splunk 集群的连接信息，支持配置/查看/清除/测试连接。

---

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

# 输出控制
log-guard -f auth.log -c --json                  # 关联分析（JSON 输出）

# Splunk / ES 连接测试与搜索（脚本可集成，退出码 0=成功 / 1=失败 / 2=DSL 非法）
log-guard --splunk-test --json                   # 测试 Splunk 连接
log-guard --splunk-search 'search index=* | head 5' --json   # 执行 SPL 搜索
log-guard --es-test --json                       # 测试 ES 连接（返回集群名/版本）
log-guard --es-search '{"query":{"match_all":{}},"size":5}' --json   # 执行 ES 查询
```

## 持久化文件说明

| 文件 | 用途 |
|------|------|
| `~/.log-guard/config.json` | LLM + ES + Splunk 连接配置 |
| `~/.log-guard/es_templates.json` | ES 查询命名模板库（预置 2 个 + 用户自定义） |
| `~/.log-guard/reports/` | 攻击溯源导出报告（Markdown/JSON） |
| `~/.log-guard/llm_cache.json` | LLM 响应缓存 |
| `~/.log-guard/rag_cache/` | RAG 向量缓存 |
