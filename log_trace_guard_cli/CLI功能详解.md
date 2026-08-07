# 日志溯源卫士 CLI 智能体 — 功能详解（v3.2）

> 独立于 Web 端的轻量级命令行版本，与 Agent 共享规则数据与版本线。
> 代码规模约 9,944 行（21 个 .py），唯一运行时依赖 requests>=2.25。
> 所有数字核对当前代码：主菜单 8 项 · script_gen 子菜单 6 项 · 30 项命令行参数
> · 5 业务模块 · AI 意图分类 6 类 · 16 攻击链 · 17 设备协议条目

---

## 零、CLI 定位与设计哲学

### 0.1 为什么要有 CLI

Web 端解决"可视化、报告、实训、非技术用户"，CLI 解决：

```
CI/CD 管道集成   → 退出码契约 + JSON 输出，直接进 Jenkins/GitHub Actions
SSH 服务器巡检   → 无 GUI 环境，一条命令出结果
批量处理         → --batch-parse / --baseline 脚本化调用
cron 定时任务    → 凌晨跑合规自查，结果落盘
```

### 0.2 与 Web 端的架构差异

| 维度 | Agent（Web） | CLI |
|------|-------------|-----|
| 并发模型 | async/await + FastAPI | 同步 requests |
| LLM | LLMFactory.get_*_llm() | LLMClient（sync） |
| RAG | ChromaDB 本地向量库 | JSON 缓存 + API 远程嵌入 |
| 上下文 | ContextManager 依赖注入 | ConversationContext（ai_core/context.py） |
| 文件读取 | API 传 file_content | LogReader 本地文件访问 |
| 数据规则 | data/rule_data/*.json（20 个） | data/rule_data/*.json（16 个） |
| 实训模块 | 完整（动态场景+评分） | 已删除（终端场景价值低，用户决策） |

### 0.3 代码结构（9,944 行）

```
log_guard/
├── cli.py                    # 2103 行：菜单/参数/展示层
├── ai_core/                  # AI 对话核心（793 行）
│   ├── intent_classifier.py  # 意图分类器（6 类）
│   ├── orchestrator.py       # 编排器：意图→模块→润色
│   ├── rag_engine.py         # RAG 引擎（JSON 向量缓存）
│   ├── llm_client.py         # LLM + Embedding 客户端
│   ├── polisher.py           # 结果润色
│   ├── prompts.py            # prompt 模板
│   ├── settings.py           # 配置
│   └── context.py            # 对话上下文
├── modules/                  # 5 业务模块（5,648 行）
│   ├── log_parse.py          # 1247 行：7 解析器 + 工厂 + Service
│   ├── log_collect.py        # 1045 行：采集/故障/设备匹配
│   ├── script_gen.py         # 1623 行：脚本生成/执行/闭环增强
│   ├── log_correlate.py      # 1042 行：关联分析/攻击链
│   └── compliance.py         # 691 行：合规问答/基线/自查
├── core/log_reader.py        # 486 行：本地文件读取
└── common/utils.py           # 311 行：工具函数
```

---

## 一、双模式交互体系

### 1.1 菜单模式（8 项主菜单）

```
┌─ 主菜单 ─────────────────────────────────────────────┐
│  📂 选择日志文件    从电脑中浏览和选择日志文件          │
│  🔍 日志解析        识别、解析、风险研判日志内容        │
│  📡 日志采集        采集方案、故障诊断、架构推荐        │
│  📝 脚本生成        正则、ES查询、攻击溯源、脚本优化    │
│  📋 合规审计        合规问答、基线生成、合规自查        │
│  🔄 联合日志审查    多源日志关联分析、攻击链推演        │
│  🤖 AI 智能对话     自由提问，AI 智能解析意图           │
│  🚪 退出                                             │
└──────────────────────────────────────────────────────┘
```

- 顶部实时显示当前已选日志文件 + 行数（上下文感知）
- 选择日志文件后，后续模块自动复用该文件（解析/审查/溯源共享数据源）
- 每个子菜单用 `_show_nav_menu` 统一渲染，支持编号/方向键/返回

### 1.2 script_gen 子菜单（6 项）

```
① 正则规则生成   根据攻防场景生成正则检测规则
② ES查询生成    生成 Elasticsearch 检索语句
③ Splunk SPL生成 生成 Splunk 搜索语句
④ 攻击溯源       分析攻击链路（6 级阶段）
⑤ 脚本优化       优化现有脚本（正则/ES查询）
⑥ 连接配置       配置 ES / Splunk 集群连接
```

### 1.3 联合日志审查子菜单（4 项）

```
① 从当前日志文件分析   对选中的日志文件做跨源关联分析
② 手动输入日志行       多行日志粘贴分析（每条一行）
③ 查看攻击链模式       查看系统支持的攻击链检测模式
④ 攻击链→溯源脚本      检测到攻击链后自动生成溯源脚本（分析→处置闭环）
```

---

## 二、AI 对话模式（意图分类 + 编排）

### 2.1 意图分类器（intent_classifier.py, 79 行）

```
6 类意图映射：
  log_parse    → log_parse     （解析日志）
  collection   → log_collect   （采集方案）
  compliance   → compliance    （合规审计）
  script_gen   → script_gen    （脚本生成）
  correlation  → log_correlate （关联分析）
  general      → None          （通用问答，不调业务模块）

流程：LLM 对用户输入做意图识别 + 置信度打分
  confidence >= intent_confidence_threshold → 调业务模块
  confidence < threshold → 走通用问答（直接 LLM 回答）
```

### 2.2 编排器（orchestrator.py, 220 行）

```
用户输入
  → intent_classifier.classify()          # 意图 + 置信度
  → 是业务意图？
      → _load_module(module_name)         # 惰性加载模块（缓存单例）
      → module.<对应方法>(提取的参数)
      → raw_result
  → ResponsePolisher.polish(module, input, raw_result)
      → LLM 把结构化结果润色成自然语言回答
  → 返回最终答复
```

- 模块惰性加载：`_load_module` 只加载当前意图需要的模块，内存友好
- 意图带参数提取：从用户输入中解析模块需要的参数（如设备类型、场景描述）
- 对话上下文保留：ConversationContext 记忆 last_intent，追问时延续上一意图

### 2.3 结果润色器（polisher.py, 71 行）

- `polish()`：模块返回结构化 dict → LLM 转自然语言（带模块上下文）
- `direct_answer()`：通用问答直接 LLM 回答，不经过模块
- 润色 prompt 区分模块，让回答风格贴合场景（如合规回答引用条款）

### 2.4 命令行为例

```bash
log-guard --ask "帮我看看这个日志是不是被爆破"      # AI 解析意图→调 log_parse
log-guard --ask "生成一个检测SQL注入的正则"          # → script_gen
log-guard --ask "防火墙日志采集方案怎么配"           # → log_collect
log-guard --ai                                    # 进入交互式 AI 对话
```

---

## 三、LLM 客户端与 RAG 引擎

### 3.1 LLMClient（llm_client.py, 197 行）

```
LLMClient.chat(messages, temperature, timeout)   # 同步 requests.post
  → 返回 {"success": bool, "content": str, ...}

LLMClient.chat_json(messages, ...)               # 带 3 层 JSON 解析恢复
  → 直解 → 括号补全 → raw_decode

EmbeddingClient.embed(text) / embed_batch(texts) # 远程嵌入 API
  → 支持批量请求，失败返回 None（降级）
```

- chat_json 内置 **3 层截断恢复**：完整 JSON → 补括号 → raw_decode，
  与 Agent 端 4 层容错同源（CLI 版简化）
- get_llm() / get_embedding() 单例工厂，reset_clients() 测试用

### 3.2 RAGEngine（rag_engine.py, 272 行）

```
load() 阶段：
  扫描 data/rule_data/*.json → _flatten_json 展平为文档列表
  → 计算规则哈希（_compute_rules_hash，内容变化才重建）
  → embed_batch 批量向量化 → 存本地 JSON 缓存（增量更新）

search(query, top_k) 阶段：
  embed(query) → 余弦相似度排序 → 返回 top_k 文档

关键设计：
  - 无本地向量库（不装 ChromaDB），向量存 JSON 文件，零重依赖
  - 哈希失效判断：rule_data 内容变 → 自动重建向量
  - 嵌入失败降级：embed 返回 None → 关键词匹配兜底
```

---

## 四、模块一：日志解析（log_parse.py, 1247 行）

### 4.1 解析器家族（7 个策略类）

```
BaseParser（ABC）→ can_parse() + parse() 模板方法
├── SSHParser        sshd 日志：Failed password / sudo 高危命令
├── WebParser        HTTP/1. 访问日志：3 种格式
├── WAFParser        WAF 拦截：11 种攻击类型中英映射
├── FirewallParser   iptables/防火墙：drop / in= / src=
├── DBParser         mysql/postgres：15 种危险 SQL 关键词
├── GenericParser    通用兜底：任意日志行的基础字段提取
└── TrafficParser    流量日志：CSV+IP 行（必须最先注册，避免误判为 web）
```

### 4.2 提取工具集（模块级函数）

```
_extract_timestamp  3 种时间格式正则
_extract_ips        提取所有 IPv4
_extract_user       提取用户名（sshd user= / for ... from）
_extract_command    提取命令（sudo COMMAND= 等）
_extract_status     提取状态（success/failure/denied）
_extract_url        提取 URL（web 日志）
```

### 4.3 LogParserFactory + LogParseService

```
LogParserFactory：
  register("ssh", SSHParser) 等 7 个策略 → get_parser(type) 分派

LogParseService：
  parse_log(line)        → 逐解析器 can_parse 匹配 → parse → LogParseResult
  parse_log_batch(lines) → 批量
  assess_risk(parsed)    → P0-P3 风险研判
  LLM 兜底：所有解析器都不匹配 → LLM 识别日志类型再解析
```

### 4.4 特色

- **解析器可扩展**：新增日志类型只需实现 BaseParser + 注册，不碰调用方
- **风险研判本地化**：assess_risk 纯本地规则，零 API 成本
- **与 Web 端同算法**：解析器逻辑与 Agent 端一致，结果可互信

---

## 五、模块二：日志采集（log_collect.py, 1045 行）

### 5.1 采集策略（策略模式）

```
BaseCollectStrategy → get_plan(device_type, device_model, ...)
├── DeviceProtocolStrategy   按 device_protocol.json（17 设备条目）匹配
└── DefaultFallbackStrategy  未命中时通用方案兜底
CollectStrategyFactory：按设备类型注册/分派
```

### 5.2 设备匹配（DeviceMatcher, 277 行起）

```
三级评分：
  精确型号匹配 → 95 分
  类型匹配     → 80 分
  模糊子串     → 50 分
17 种设备：paloalto / fortigate / usg / asa / iptables / modsecurity /
          yundun / anquanbao / linux / windows / mysql / postgresql /
          sqlserver / oracle / nginx / apache / iis
```

### 5.3 故障诊断（FaultFixer, 412 行起）

```
输入：错误描述 + 设备类型 + 协议
流程：
  → fault_kb.json（9 类故障）关键词匹配
  → 命中 → 输出原因分析 + 解决步骤
  → 未命中 → LLM 诊断兜底
  → 输出：fault_type / confidence / reason / solution
9 类故障：ssh_connect_failure / network_timeout / ssh_auth_failure /
         port_unreachable / log_lost / format_error / time_offset /
         transport_interrupt / storage_failure
```

### 5.4 特色

- 架构推荐能力（Agent 端迁至 advisory 模块）在 CLI 仍保留于采集子菜单
- 故障诊断带"原因 → 步骤"结构化输出，可直接粘贴给运维执行

---

## 六、模块三：脚本生成（script_gen.py, 1623 行，CLI 最大模块）

### 6.1 三大生成策略 + 工厂

```
BaseScriptStrategy → generate(params)
├── RegexGenStrategy     正则生成（4 级级联）
│   _identify_scene      场景识别（scene_keywords.json 打分）
│   _get_fallback_rules  兜底规则（fallback_rules.json）
├── EsQueryGenStrategy   ES 查询生成（场景关键词评分 + 模板 + RAG 兜底）
└── TraceStrategy        攻击溯源（trace_patterns.json 6 级阶段）
ScriptStrategyFactory：register("regex"/"es_query"/"trace") → get_strategy
```

### 6.2 一键执行能力

```
execute_es_query(query_dict, index_pattern)
  → 标准 ES REST API（/{index}/_search），兼容 v7/v8
  → 返回：命中总数、耗时、分片状态、前 N 条样本

test_regex_on_file(regexes, log_lines)
  → 纯本地 re.compile 测试，文件上限 5000 行
  → 返回：每条规则的匹配数/总行数/匹配率 + 前 5 条样本

execute_splunk_query(spl_query, splunk_config)
  → Splunk REST API：POST /services/search/jobs → 轮询 → GET results
  → 标准库 urllib.request + base64，零第三方依赖

generate_splunk_query(search_scenario, index, time_range)
  → 5 场景模板：SSH爆破 / SQL注入 / Web攻击 / 异常流量 / 数据泄露 + 自定义
  → 中文场景名智能匹配（scene_label + 关键字组合打分）
  → time_map：last_1h/-1h@h、last_4h、last_24h、last_7d、last_30d
```

### 6.3 闭环增强四件套（v3.2 核心）

```
① 溯源报告导出 export_trace_report(trace_data, output_path)
   → Markdown/JSON 双格式，保存 ~/.log-guard/reports/trace_report_*.md
   → 含攻击链分段、时间线表格、摘要、生成时间

② ES 查询模板管理（~/.log-guard/es_templates.json）
   save_es_template / list_es_templates / load_es_template / delete_es_template
   内置预置模板：SSH爆破检测、SQL注入检测
   子菜单入口：ES 查询生成后询问"是否保存为模板" + "管理 ES 查询模板"

③ 溯源 → 监控规则（闭环）trace_to_monitoring_rules(trace_data)
   → 从 attack_chain 自动提取 keywords + IPs
   → 同时生成 ES Query DSL（match_bool）+ 正则规则列表
   → 展示后询问"是否将 ES 查询保存为模板？" → 一键存入模板库
   → 意义：分析一次攻击 → 生成持续监控规则

④ Splunk SPL 生成 + 执行
   → 5 种场景模板，中文场景名匹配
   → 支持配置 Splunk 连接（config.json splunk 字段）
   → 测试连接 / 执行 SPL / 展示结果
```

### 6.4 连接配置持久化（双平台）

```
ES 配置：     ~/.log-guard/config.json 的 "es" 字段（load_es_config/save_es_config）
Splunk 配置： ~/.log-guard/config.json 的 "splunk" 字段（load/save_splunk_config）
子菜单入口：script_gen 子菜单第 6 项"连接配置"（_menu_es_config / _menu_splunk_config）
设计：企业多分析师共享场景，换设备不丢配置（用户明确要求）
```

### 6.5 脚本优化器

```
optimize_script(script, script_type)
  _optimize_regex    → re.compile 编译检查 + 性能/安全性建议
  _optimize_es_query → JSON 有效性 + query 字段存在性 + DSL 结构建议
```

---

## 七、模块四：合规审计（compliance.py, 691 行）

### 7.1 三大策略 + 工厂

```
BaseComplianceStrategy → execute(params)
├── QAStrategy          合规问答：标准库检索 → LLM 解读
├── BaselineGenStrategy 基线生成：资产规模自适应
└── CheckStrategy       合规自查：8 项硬编码检查
ComplianceStrategyFactory：register("qa"/"baseline"/"check")
```

### 7.2 标准库数据

```
compliance_standards.json（3 条）：
  等保 2.0（8 项要求）/ 网络安全法 / 数据安全法

compliance_baselines.json（7 条）：
  6 大监控场景 × 资产规模自适应（<30 宽松 / 30-500 标准 / >500 严格）
```

### 7.3 自查评分算法

```
8 项检查（日志留存/覆盖/备份/访问控制/加密/告警/审计/应急）
评分：max(0, 100 - (critical×30 + high×15 + medium×8 + low×3))
```

### 7.4 特色

- `--qa "等保2.0对日志留存要求"` 一行命令合规问答
- `--baseline 50` 直接生成 50 台资产的个性化基线
- 检查项 REQUIREMENTS 字典硬编码在 CheckStrategy，可扩展

---

## 八、模块五：联合日志审查（log_correlate.py, 1042 行）

### 8.1 双引擎架构（与 Web 端同源）

```
AttackChainMatcher（关键词引擎）
  _load_rules → correlation_patterns.json（16 攻击链）
  match(log_lines) → 正则匹配所有规则 keyword patterns
  → 命中即返回（毫秒级）

LLMChainAnalyzer（语义引擎）
  analyze(log_lines) → 一次性发送所有行 → LLM 返回攻击链 JSON
  _parse_llm_json → 4 层容错（完整 JSON → 截断修复 → 正则提取 → 关键词兜底）

LogCorrelateService.correlate_logs(use_llm)
  use_llm=False：关键词先跑，未命中才 LLM 兜底
  use_llm=True ：双引擎合并（按 chain_name 去重取 max confidence，method=hybrid）
```

### 8.2 16 种攻击链

```
SSH爆破提权 / 暴力破解 / SQL注入 / Web扫描利用 / 入口入侵→横向移动 /
权限提升 / 数据窃取 / C2通信 / 勒索软件 / 内网侦察 / Web攻击→数据窃密 /
DNS隧道 / 供应链攻击 / 内部威胁 / WAF绕过→攻击成功 / 认证失败
```

### 8.3 时序推理（CLI 版）

```
TimelineBuilder（time_window_minutes 默认 5 分钟）
  build_timeline → 按时间窗口聚合相关事件 → 攻击链时间线
CorrelatedEvent 提供 matches_device_type / matches_status / matches_command
ChainAnalyzer 按 pattern 的 stages 逐阶段匹配
```

### 8.4 攻击链 → 溯源脚本（闭环）

```
to_trace_script(chain_name, ...)
  → _infer_attack_type(chain_name)：16 链名 → 7 种 trace 类型
    （ssh_brute→brute_force、sql_injection→sql_injection 等）
  → 复用 script_gen 的溯源能力 + 导出报告 + 生成监控规则
  → 子菜单第 4 项"攻击链→溯源脚本"
```

### 8.5 特色

- **与 Web 端完全同源**：correlation_patterns.json 同一份规则，检测结果一致
- **CLI 文件通道**：correlate_logs_from_file 直接读本地文件分析
- **可用 patterns 查询**：available_patterns() 列出全部攻击链模式

---

## 九、命令行参数全表（30 项）

### 9.1 核心参数

| 参数 | 别名 | 说明 |
|------|------|------|
| `--version` | `-V` | 显示版本号 |
| `--ai` | | 直接进入 AI 智能对话模式 |
| `--ask` | | 非交互式 AI 问答（输出 JSON） |
| `--json` | | 强制 JSON 输出（适合脚本调用） |
| `--log-file` | `-f` | 日志文件路径 |
| `--log-dir` | `-d` | 日志文件目录 |
| `--list-logs` | `-l` | 列出常见位置日志文件 |
| `--sample` | `-s` | 预览日志（默认 20 行） |
| `--parse` | `-p` | 解析日志（可传日志行字符串） |
| `--batch-parse` | `-b` | 批量解析 |
| `--assess` | `-a` | 解析时同时风险研判 |
| `--lines` | `-n` | 读取行数（默认 100） |
| `--grep` | `-g` | 关键词过滤 |
| `--diagnose` | | 故障诊断 |
| `--device-type` | | 设备类型 |
| `--protocol` | | 传输协议 |
| `--error-log` | | 错误日志内容 |
| `--regex` | | 正则规则生成 |
| `--log-sample` | | 日志样例 |
| `--qa` | | 合规问答 |
| `--es-query` | | ES 查询生成 |
| `--baseline` | | 合规基线生成（可选资产数量，默认 10） |
| `--optimize` | | 脚本优化（脚本 + 类型: regex/es_query） |
| `--asset-type` | | 资产类型 |
| `--correlate` | `-c` | 联合日志审查 |
| `--time-window` | `-w` | 关联时间窗口（分钟，默认 5） |
| `--splunk-test` | | 测试 Splunk 连接 |
| `--splunk-search` | | 执行 Splunk 搜索（传 SPL 查询） |
| `--es-test` | | 测试 ES 连接 |
| `--es-search` | | 执行 ES 搜索（传 DSL JSON） |

### 9.2 退出码契约（CI 集成关键）

```
0 = 成功
1 = 连接失败（Splunk/ES）
2 = DSL/SPL 非法
配合 --json 输出，可直接在 CI 管道判断成功/失败
```

### 9.3 命令行示例

```bash
log-guard -f /var/log/auth.log --parse            # 解析日志
log-guard -f auth.log --parse --assess --json     # 解析+研判+JSON 输出
log-guard --ask "什么是SQL注入"                    # AI 问答
log-guard --diagnose "SSH connection timeout"     # 故障诊断
log-guard --regex "detect SQL injection"          # 生成正则
log-guard --regex "SQL注入" --log-sample "..."    # 带样例生成
log-guard --baseline 50                           # 合规基线
log-guard --correlate -f multi.log -w 10          # 关联分析（10 分钟窗口）
log-guard --es-search '{"query":{"match_all":{}}}' # 执行 ES 查询
log-guard --splunk-search 'index=linux sshd'      # 执行 Splunk 查询
log-guard --splunk-test                           # 测试 Splunk 连接
log-guard --version                               # v3.2
```

---

## 十、工程化与版本维护

### 10.1 测试体系

```
243 passed + 1 skipped（12 个 pytest 文件）
CI 命令：python3.10 -m pytest tests/ -q --cov=log_guard --cov-fail-under=35
覆盖率：43.4%（门槛 35%）
```

### 10.2 版本号五处同步（历史教训 f3e6f6b）

| 位置 | 文件 |
|------|------|
| 打包元数据 | pyproject.toml version |
| 打包元数据 | setup.py version |
| 运行显示 | cli.py 4 处（docstring/banner/argparse description/--version） |
| 文档 | README.md 标题 + 新功能小节 |
| CI 发布 | release-cli.yml（已自动读取 pyproject.toml） |

### 10.3 发布流程

```
generate_changelog.py --dry-run   # 本地预览变更日志
git tag v3.2.0-日期               # release-cli.yml 自动打 tag + release notes
pip install -e . --user --no-build-isolation  # 刷新 pip metadata
```

### 10.4 配置存储

```
~/.log-guard/config.json：
  es      字段（host/port/scheme/username/password）
  splunk  字段（host/port/scheme/token/username/password）
  api_key + base_url（LLM 配置）
~/.log-guard/es_templates.json     # ES 查询模板库
~/.log-guard/reports/              # 溯源报告输出目录
```

---

## 十一、CLI 特色亮点总结

1. **零依赖部署**：唯一运行时依赖 requests>=2.25，
   SPL/ES 执行用 urllib.request + base64 标准库实现，任何服务器 pip install 即用
2. **双模式无缝切换**：菜单模式适合交互，AI 对话模式适合自然语言，
   命令行模式适合脚本化 —— 三态覆盖所有使用场景
3. **与 Web 端同源可信**：16 攻击链、解析器算法、合规标准库全部共享，
   两边结果一致，CLI 可作 Web 的离线验证工具
4. **分析 → 处置闭环**：攻击链 → 溯源脚本 → 报告导出 → 监控规则生成，
   "分析一次攻击，生成持续监控"（v3.2.1 核心增强）
5. **CI 友好**：退出码契约 + --json 输出 + 30 项参数全覆盖，可直接进管道
6. **RAG 轻量化**：无 ChromaDB，向量存 JSON 缓存 + 哈希失效重建 + 嵌入失败降级，
   重依赖全部规避
7. **配置持久化**：ES/Splunk 连接配置存 ~/.log-guard/config.json，
   企业多分析师换设备不丢配置
8. **终端适配套装**：溯源报告导出 Markdown/JSON、ES 模板管理、SPL 一键执行
   —— 全部适配纯终端环境，不依赖浏览器
