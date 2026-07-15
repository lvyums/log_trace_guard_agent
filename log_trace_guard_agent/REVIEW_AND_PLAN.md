# 代码审查报告 & 下一阶段开发计划

> 审查时间: 2026-07-15
> 审查范围: 模块一（log_parse）、模块三（log_collect）、core 底座层、common 工具层、app 层
> 设计文档: 日志溯源卫士智能体-详细设计.md

---

## 第一部分：共性架构问题审查（两轮复盘）

### 一、架构分层与解耦

#### ✅ 已做对的地方
- 两个模块之间没有互相 import，符合「modules 零耦合」规范
- 都通过 `core/context_manager.py` 传递跨模块数据
- 工厂模式使用外部 `register()` 注册（LogParserFactory, CollectStrategyFactory）
- 五层分层结构（app → modules → core → common）基本清晰

#### ❌ 遗留问题（Phase 1b 必须修复）

| 编号 | 严重度 | 问题 | 位置 | 说明 |
|------|--------|------|------|------|
| A1 | 🔴 高 | **特征识别硬编码在业务层** | `log_parse/service.py` L249-266 | `_extract_features()` 中特征权重表写死在业务代码，应抽到 `data/rule_data/` 外部配置 |
| A2 | 🔴 高 | **架构推荐内容硬编码在 service** | `log_collect/service.py` L269-300 | `_recommend_arch_by_threshold()` 返回的推荐文本、组件列表、成本估算全部硬编码 |
| A3 | 🟡 中 | **LLMFactory 未使用注册模式** | `core/ai_base/llm_factory.py` L82-103 | `create()` 内部硬编码 `DeepSeekClient`/`LightweightClient`，新增模型需改源码 |
| A4 | 🟡 中 | **ContextManager 使用 dataclass 而非 Pydantic** | `core/context_manager.py` L9-17 | `ModuleContext` 是 dataclass，但 `context_schema.py` 已定义 `ModuleContextSchema`，未使用 |
| A5 | 🟢 低 | **函数内部重复导入** | `log_parse/service.py` L243 | `_extract_features` 中重复 import `RiskBaseline`（文件顶部已导入） |
| A6 | 🟢 低 | **函数内部 import settings 散落** | `log_collect/service.py` L37, L214 | 多处从函数内部 `from app.settings import settings`，应统一在文件顶部 |

### 二、配置与硬编码

#### ✅ 已做对的地方
- `settings.py` 定义了 DeviceType、CollectProtocol、RiskLevel、ScaleLevel 枚举
- 设备映射从 `device_protocol.json` 加载
- 故障知识库从 `fault_kb.json` 加载
- 采集模板从 `collect_templates.json` 加载
- `JsonConfigLoader` 支持缓存和热加载

#### ❌ 遗留问题

| 编号 | 严重度 | 问题 | 位置 | 说明 |
|------|--------|------|------|------|
| B1 | 🔴 高 | **风险基线全部硬编码在代码** | `risk_baseline.py` L56-120 | 7条风险规则全部写死在 `_register_default_rules()` 中，无法热更新 |
| B2 | 🔴 高 | **日志特征识别表硬编码** | `log_parse/service.py` L249-266 | SSH/Web 特征关键词和权重硬编码 |
| B3 | 🟡 中 | **字符串魔法值散落** | `log_parse/service.py` L150 | `risk_counts` 字典使用手写 `"P0_高危"` 等，未引用 `RiskLevel` 枚举 |
| B4 | 🟡 中 | **架构推荐文本硬编码** | `log_collect/service.py` L271-299 | 三套架构推荐文本全部硬编码，应抽到 JSON 配置 |

### 三、设计模式标准化

#### ✅ 已做对的地方
- `BaseParser` 抽象基类 + `LogParserFactory` 注册模式
- `BaseCollectStrategy` 抽象基类 + `CollectStrategyFactory` 注册模式
- `BaseLLMClient` 抽象基类
- `CollectPlan` / `FaultDiagnosis` 结构化载体

#### ❌ 遗留问题

| 编号 | 严重度 | 问题 | 位置 | 说明 |
|------|--------|------|------|------|
| C1 | 🔴 高 | **LLMFactory 无注册机制** | `llm_factory.py` L82-103 | 新增模型类型必须修改 `create()` 方法 |
| C2 | 🟡 中 | **解析器输出无强制结构体** | `base_parser.py` L18-22 | `parse_fields()` 返回裸 dict，字段不统一 |
| C3 | 🟡 中 | **RiskBaseline 无外部注册机制** | `risk_baseline.py` L56-120 | 规则写在代码中，应改为从 JSON 文件加载 + 外部 `register_rule()` |

### 四、健壮性与边界处理

#### ✅ 已做对的地方
- 入参使用 Pydantic model 校验（`LogIdentifyReq`, `DeviceMatchReq` 等）
- `FaultFixer.diagnose()` 返回 None 时 service 有兜底
- `CollectStrategyFactory` 有 `GenericSyslogStrategy` 兜底
- `RiskBaseline` 有 `GEN-001` 兜底规则
- `app/exceptions.py` 定义了自定义业务异常和全局异常处理器

#### ❌ 遗留问题

| 编号 | 严重度 | 问题 | 位置 | 说明 |
|------|--------|------|------|------|
| D1 | 🟡 中 | **router 中手动校验与 Pydantic 重复** | `log_parse/router.py` L24-26, L35-37, L61, L71, L81 | 已有 Pydantic 约束，又手动调 `validate_log_line()` 和空值检查 |
| D2 | 🟡 中 | **无法识别日志时返回空+错误** | `log_parse/service.py` L88-91 | 返回 `Result.fail()`，没有兜底方案（应返回通用解析+人工复核提示） |
| D3 | 🟢 低 | **部分异常直接返回而非抛出** | `log_parse/router.py` L26, L37 | 使用 `return make_response()` 而非 `raise ParamInvalidException()` |

### 五、数据模型与上下文

#### ✅ 已做对的地方
- `app/schemas/` 定义了完整的 Pydantic 入参/出参模型
- `context_schema.py` 定义了 `ModuleContextSchema` 和 `RequestContextSchema`
- 上下文绑定 request_id，支持 TTL 过期清理

#### ❌ 遗留问题

| 编号 | 严重度 | 问题 | 位置 | 说明 |
|------|--------|------|------|------|
| E1 | 🟡 中 | **ContextManager 内部使用 dataclass 而非 Pydantic** | `context_manager.py` | `ModuleContext` 是 dataclass，`context_schema.py` 的 `ModuleContextSchema` 未使用 |
| E2 | 🟢 低 | **上下文创建时 user_input 传空字符串** | `dependencies.py` L66-69 | `get_context()` 创建 ContextManager 时传空字符串，丢失原始输入 |

### 六、复用性与工程规范

#### ✅ 已做对的地方
- `common/` 下有 7 个工具模块（logger, file_util, ip_util, time_util, str_util, result_util, json_util）
- 两个模块都有批量接口（`/parse/batch`, `/plan/batch`）
- 两个模块都调用了 RAG 知识库

#### ❌ 遗留问题

| 编号 | 严重度 | 问题 | 位置 | 说明 |
|------|--------|------|------|------|
| F1 | 🟢 低 | **`result_util.py` 和 `exceptions.py` 都有 `make_response`** | 两个文件 | 返回封装逻辑重复，应统一使用 `Result` 类 |

### 七、迭代扩展

#### ✅ 已做对的地方
- `JsonConfigLoader` 支持 `reload()` 热加载
- `DeviceMatcher.reload_config()` / `FaultFixer.reload_kb()` / `RegexRuleEngine.reload()` 支持热加载
- 新增解析器：新建文件 + `register()`
- 新增采集策略：新建文件 + `register()`

#### ❌ 遗留问题

| 编号 | 严重度 | 问题 | 位置 | 说明 |
|------|--------|------|------|------|
| G1 | 🔴 高 | **风险规则无法热更新** | `risk_baseline.py` | 规则写死在代码中，修改必须重启服务 |
| G2 | 🟡 中 | **LLM 模型切换需要改工厂代码** | `llm_factory.py` | 新增模型类型需要修改 `create()` 方法 |

---

## 第二部分：修复优先级与执行计划

### Phase 1b 修复（当前阶段，立即执行）

| 优先级 | 问题编号 | 修复内容 | 预计工作量 |
|--------|----------|----------|-----------|
| P0 | B1, C3 | 风险基线抽到 `data/rule_data/risk_rules.json`，`RiskBaseline` 改为外部配置加载 | 2h |
| P0 | A1, B2 | 日志特征识别表抽到 `data/rule_data/log_features.json`，`_extract_features` 改为配置驱动 | 1h |
| P0 | A2, B4 | 架构推荐文本抽到 `data/rule_data/arch_templates.json` | 1.5h |
| P1 | C1, G2 | LLMFactory 改为注册模式，支持外部 `register()` 注册客户端类 | 1.5h |
| P1 | A4, E1 | ContextManager 改用 Pydantic 的 `ModuleContextSchema` 替代 dataclass | 1h |
| P2 | D2 | 日志无法识别时返回「通用解析 + 人工复核提示」兜底，而非直接 fail | 0.5h |
| P2 | D1 | 清理 router 中与 Pydantic 重复的手动校验，统一到 schema 层面 | 0.5h |

### Phase 2 优化（模块四开发前完成）

| 优先级 | 问题编号 | 修复内容 | 预计工作量 |
|--------|----------|----------|-----------|
| P2 | B3 | 字符串魔法值统一替换为 `RiskLevel` 枚举引用 | 0.5h |
| P2 | A5, A6 | 清理函数内部重复/散落的 import | 0.3h |
| P2 | E2 | `get_context()` 注入时传递用户输入到 ContextManager | 0.3h |
| P3 | C2 | `BaseParser.parse_fields()` 返回结构化 Pydantic model | 1h |
| P3 | F1 | 统一 `make_response` 和 `Result` 的返回封装 | 0.5h |

---

## 第三部分：下一阶段开发（模块四：技术赋能脚本生成模块）

### 开发前必须完成的前置修复

1. ✅ **风险基线外部化**（B1, C3）— 否则模块四的脚本规则无法联动知识库
2. ✅ **特征识别表外部化**（A1, B2）— 模块四的脚本生成需要统一特征库
3. ✅ **LLMFactory 注册化**（C1, G2）— 模块四需要调用 LLM 生成脚本

### 模块四架构设计要点

```
modules/script_gen/
├── script_strategy.py     # 策略抽象基类 + 工厂注册
├── regex_gen.py           # 正则生成策略
├── es_sql_gen.py          # ES/SQL 检索语句生成策略
├── platform_choose.py     # 平台选型策略
├── trace_link.py          # 攻击链路溯源策略
├── service.py             # 业务编排
├── router.py              # 接口路由
└── __init__.py
```

### 强制遵守的约束（基于复盘总结）

1. **模块四禁止 import 模块一/三任何代码**
2. **所有策略类继承抽象基类，工厂使用 `register()` 注册**
3. **所有映射数据存放在 `data/rule_data/`，代码零硬编码字符串**
4. **入参使用 Pydantic schema，未知场景必须兜底**
5. **跨模块数据通过 `core/context_manager` 上下文传递**
6. **通用工具（文件/字符串/JSON）全部复用 `common/` 已有工具**
7. **脚本生成需要联动 RAG 知识库分片（scripts 库）**
8. **接口成对设计：单条 + 批量**
9. **新增场景仅新增策略文件 + 注册，不修改原有核心代码**
10. **LLM 调用走 `LLMFactory` 注册后的统一入口**

### 模块四接口设计

```
POST /api/v1/script-gen/regex         # 生成正则规则
POST /api/v1/script-gen/regex/batch   # 批量生成正则
POST /api/v1/script-gen/es-query       # 生成 ES 检索语句
POST /api/v1/script-gen/platform       # 平台选型推荐
POST /api/v1/script-gen/trace          # 攻击链路溯源
POST /api/v1/script-gen/optimize       # 脚本优化纠错
```

### 开发交付校验清单（每个接口完成后自查）

```
[ ] 模块间无互相 import
[ ] 无硬编码映射/阈值/配置文本
[ ] 策略有抽象基类，工厂使用注册模式
[ ] 全链路入参有 schema 校验，未知场景有兜底
[ ] 跨模块数据使用标准化上下文结构体
[ ] 通用逻辑全部复用 common/core 工具
[ ] 支持批量操作、联动 RAG 分片知识库
[ ] 新增功能无侵入修改原有核心代码
```