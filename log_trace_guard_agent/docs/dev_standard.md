# 日志溯源卫士智能体 — 全局开发规范

> 版本: 1.0.0
> 所有模块开发、重构、接口编写必须严格遵循本规范。

---

## 一、五层分层架构

```
app/ → modules/ → core/ → common/ → data/
```

### 1.1 分层职责

| 层 | 目录 | 职责 | 禁止 |
|----|------|------|------|
| 应用层 | `app/` | FastAPI 入口、路由挂载、全局异常、依赖注入、Pydantic Schema | 写业务逻辑 |
| 业务模块层 | `modules/` | 七大业务模块，互相零耦合 | 模块间互相 import |
| 核心底座层 | `core/` | AI工厂、规则引擎、上下文管理器、数据预处理 | 依赖业务模块 |
| 公共工具层 | `common/` | 日志、文件、字符串、JSON、返回封装工具 | 依赖业务/core |
| 数据层 | `data/` | 向量库、规则库、案例库、临时文件 | 写业务逻辑 |

### 1.2 调用方向

**允许：** `app → modules → core → common → data`
**禁止：** 逆向调用（common 不可 import core 或 modules，core 不可 import modules）

### 1.3 Modules 零耦合

- `modules/` 下各业务模块**禁止互相 import**
- 跨模块数据统一通过 `core/context_manager.py` 传递
- 跨模块能力统一调用 `core/` 或 `common/` 层

---

## 二、设计模式规范

### 2.1 策略模式

所有多分支场景必须使用抽象基类 + 策略模式：

```python
from abc import ABC, abstractmethod

class BaseXxxStrategy(ABC):
    @abstractmethod
    def execute(self, params: dict) -> dict: ...
    @abstractmethod
    def can_handle(self, params: dict) -> bool: ...
```

### 2.2 工厂注册模式

所有实例管理必须使用 `register()` 外部注册模式：

```python
class XxxFactory:
    _strategies: dict[str, type[BaseXxxStrategy]] = {}

    @classmethod
    def register(cls, name: str, strategy_cls: type[BaseXxxStrategy]):
        cls._strategies[name] = strategy_cls

    @classmethod
    def get_strategy(cls, name: str) -> Optional[BaseXxxStrategy]:
        strategy_cls = cls._strategies.get(name)
        return strategy_cls() if strategy_cls else None
```

**禁止：** 在工厂 `create()` 方法内部硬编码 `if-else` 实例化策略。

---

## 三、配置与硬编码禁令

### 3.1 必须外置的数据类型

| 类型 | 存放位置 | 示例 |
|------|---------|------|
| 静态映射表 | `data/rule_data/*.json` | 设备协议映射、场景关键词 |
| 知识库/故障库 | `data/rule_data/*.json` | 风险规则、故障知识 |
| 配置模板 | `data/rule_data/*.json` | 正则模板、ES查询模板 |
| 数值阈值 | `app/settings.py` 或 `data/rule_data/*.json` | 评分阈值、超时时间、数量限制 |
| 推荐文本 | `data/rule_data/*.json` | 架构推荐、平台选型文案 |

### 3.2 硬编码判定标准

以下情况均视为**违规硬编码**：
- 代码中直接写字符串映射表（`{"ssh": ["爆破", "brute"], ...}`）
- 代码中直接写正则表达式（非从外部加载）
- 代码中直接写数值阈值（如 `score += 20`、`if len > 200`）
- 代码中直接写推荐文案、描述文本
- 风险等级、状态枚举值在业务代码中手写字符串（应引用枚举）

### 3.3 正确做法

```python
# ❌ 禁止：硬编码
SCENE_KEYWORDS = {"ssh": ["爆破", "brute"], "web": ["http", "sql注入"]}

# ✅ 正确：外部加载
config_path = f"{settings.rule_data_dir}/script_gen_scene_keywords.json"
keywords = JsonConfigLoader.load(config_path) or {}
```

---

## 四、参数校验规范

### 4.1 入参

- 所有 API 入参必须使用 `app/schemas/` 下的 Pydantic 模型
- 必须使用 `Field(..., max_length=N, pattern=..., ge=..., le=...)` 约束
- 非法参数抛出统一业务异常，不返回原生 Python 异常

### 4.2 出参

- 所有 API 出参使用 Pydantic 响应模型
- 统一通过 `common/result_util.Result` 封装返回

### 4.3 跨模块上下文

- 所有跨模块数据传递使用 `context_schema.py` 标准化结构体
- 禁止自由字典传递
- 必须包含 `module_id`、`status`、`input`、`output`、`error_info` 字段

---

## 五、兜底设计规范

### 5.1 必须兜底的场景

| 场景 | 兜底方案 |
|------|---------|
| 未知设备类型 | 返回通用方案 + 「请人工复核」提示 |
| 模糊/空输入 | 返回默认值 + 提示信息 |
| 策略无法匹配 | 返回通用兜底策略 |
| 外部配置加载失败 | 返回内嵌默认值或降级方案 |
| RAG 检索无结果 | 返回规则层结果 + 标注「未命中知识库」 |
| LLM 调用超时/异常 | 返回规则层+RAG层结果 + 标注「LLM超时」 |

### 5.2 禁止行为

- 返回空 `None` 或空列表而不提示
- 抛出原生 Python 异常（如 `KeyError`、`ValueError`）
- 返回 `Result.fail()` 后无任何兜底信息

---

## 六、工具复用规范

### 6.1 通用工具清单

| 功能 | 工具模块 | 禁止自行实现 |
|------|---------|-------------|
| 日志输出 | `common/logger.py` | `print()`、`logging.basicConfig()` |
| 文件读写 | `common/file_util.py` | `open()` 裸操作 |
| IP 处理 | `common/ip_util.py` | 手写正则匹配 IP |
| 时间格式化 | `common/time_util.py` | 手写时间格式 |
| 字符串处理 | `common/str_util.py` | 手写清洗/转义 |
| JSON 配置加载 | `common/json_util.py` | `json.load(open())` |
| 返回封装 | `common/result_util.py` | 手动构造响应字典 |

---

## 七、RAG 知识库集成规范

### 7.1 必须调用 RAG 的场景

所有业务模块涉及知识库查询场景，必须调用 `core/ai_base/rag_factory.py` 分片检索，禁止纯硬编码规则实现。

### 7.2 知识库分片

| 分片名称 | 用途 | 调用方 |
|---------|------|--------|
| `log_basics` | 日志基础库 | 日志解析 |
| `compliance` | 合规审计库 | 合规审计 |
| `collection` | 采集架构库 | 日志采集 |
| `scripts` | 技术脚本库 | 脚本生成 |
| `cases` | 实训案例库 | 攻防实训 / 威胁狩猎 |

### 7.3 RAG 调用规范

```python
from core.ai_base.rag_factory import RAGFactory

rag = await RAGFactory.get_kb("scripts")
results = await rag.retrieve(query=scenario, top_k=3)
if results:
    # 使用 RAG 结果增强策略输出
    ...
else:
    # 降级：使用规则层结果，标注未命中知识库
    note = "未检索到知识库匹配内容，结果仅供参考"
```

---

## 八、扩展规范

### 8.1 新增功能原则

- 新增场景仅新增策略文件 + 外部注册，**不修改工厂核心代码**
- 新增映射数据仅新增/修改 JSON 配置文件，**不修改业务代码**
- 新增工具方法优先考虑 `common/` 已有模块扩展

### 8.2 接口设计

- 接口成对设计：单条 + 批量
- 批量接口限制最大数量（默认 20）
- 接口路径统一：`/api/v1/{module}/{action}[/batch]`

---

## 九、交付前自查清单

每条交付前必须逐条自查，全部通过才可交付：

```
[ ] 1. 模块间无互相 import
[ ] 2. 无硬编码映射/阈值/配置文本（全部外置）
[ ] 3. 策略有抽象基类，工厂使用注册模式
[ ] 4. 全链路入参有 Pydantic 校验，未知场景有兜底
[ ] 5. 跨模块数据使用标准化上下文结构体
[ ] 6. 通用逻辑全部复用 common/core 工具
[ ] 7. 涉及知识库场景已调用 RAG 分片检索
[ ] 8. 支持批量操作
[ ] 9. 新增功能无侵入修改原有核心代码
[ ] 10. 测试用例全覆盖边界场景，无失败用例
```

---

## 十、重复踩坑核心约束（重点重读）

1. **modules 业务模块禁止互相 import**，跨模块数据仅通过 core 上下文传递，跨模块能力统一调用 core/common 底层；
2. **所有工厂必须使用 register 外部注册模式**，禁止内部硬编码实例化策略；
3. **映射表、故障库、模板、阈值禁止写死代码**，统一存放 settings 或 data/rule_data 外部 JSON；
4. **所有入参必须使用 app/schemas Pydantic 模型校验**，未知场景必须提供兜底方案；
5. **新增功能仅新增策略/配置文件**，不修改原有核心工厂、Service 逻辑；
6. **所有跨模块上下文必须使用 context_schema 标准化结构体**，禁止自由字典传递。