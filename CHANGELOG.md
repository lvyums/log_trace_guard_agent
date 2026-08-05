# 更新日志

本文件记录「日志溯源卫士智能体」所有版本的变更内容。

---

## [v3.2.0] - 2026-08-04

### 新增功能

- **Splunk / ES 实际执行接入** — 不再只是生成脚本，可真实查询：
  - Splunk：搜索执行（SPL 轮询任务）、连接测试、Splunk Web UI 跳转链接
  - ES：Query DSL 搜索执行、连接测试（返回集群名 + 版本号）
  - Web 端系统设置新增 Splunk / Elasticsearch 配置面板（测试连接 / 临时保存 / 保存到 .env）
- **Splunk/ES 配置持久化对称** — 新增 `POST /api/v1/script-gen/splunk/config` 与 `/es/config`，前端「保存到 .env」写入后端 `.env` 全局生效
- **CLI 命令行模式扩展** — 新增 `--splunk-test` / `--splunk-search` / `--es-test` / `--es-search`，支持 `--json`，退出码契约 0=成功 / 1=连接失败 / 2=DSL 非法，可脚本集成
- **攻击链 → 实训场景一键转化** — 新增 `POST /api/v1/log-correlate/to-scenario`：关联分析结果一键下发为实战实训场景（LLM 动态生成场景 + 任务 + 标准答案），前端弹窗区分场景/溯源模式，支持「立即进入实训」跳转
- **script-gen 四大增强** — 溯源报告导出（Markdown/JSON，`~/.log-guard/reports/`）、ES 查询模板管理（内置 SSH 爆破/SQL 注入模板）、溯源 → 监控规则闭环（自动生成 ES DSL + 正则）、Splunk SPL 生成 + REST API 一键执行（5 大中文场景模板）
- **ES 查询执行入口** — 前端 EsQuery.vue 新增「执行查询」按钮，生成 DSL 后直接查库
- **本地联调环境** — `scripts/dev/mock_services.py`（mock Splunk :18089 + mock ES :19200）+ `test_api_connect.py`（18 项）/ `test_cli_connect.py`（16 项）回归脚本

### 修复

- **es_save_config 路径 bug** — 修复 .env 写入路径多嵌套 3 层 + None 值污染配置文件问题
- **Splunk Bearer Token 兼容** — Token 自动补 `Bearer ` 前缀，带前缀粘贴也不出错
- **CI 测试修复** — Agent（145）与 CLI（243）全部通过，覆盖修复回归
- **CLI 双副本收敛** — 删除历史嵌套僵尸快照，统一为仓库根 `log_trace_guard_cli/`

### 文档

- 新增 `docs/splunk-es配置说明.md` — Splunk/ES 全量接入说明（Web + CLI + 联调验证）
- 更新 `docs/生产部署指南.md` — 生产环境 ES/Splunk 配置策略（Docker / systemd / 多用户）
- 仓库根 README 更新至 v3.2（7 大模块、CLI 命令行模式、Splunk/ES 接入）

### 变更文件

- `modules/script_gen/` — Splunk/ES 搜索、测试、配置持久化路由与服务
- `modules/log_correlate/` — to-scenario 实训转化接口（temporal.py 场景生成）
- `modules/training/` — TaskEngine.inject_scenario() 动态场景注入
- `frontend/src/modules/log-correlate/Analyze.vue` — 场景/溯源模式弹窗
- `frontend/src/modules/script-gen/EsQuery.vue` — 执行查询入口
- `log_trace_guard_cli/log_guard/cli.py` — Splunk/ES 命令行模式
- `scripts/dev/` — mock 服务 + 联调回归脚本
- `app/main.py` — 版本号更新至 3.2.0

---

## [v3.1.0] - 2026-07-25

### 新增功能

- **规划咨询模块** — 新增独立 advisory 模块，分离架构推荐与平台选型功能
- **基线报告下载** — 合规基线报告支持 Markdown 格式下载

### 重构

- **模块职责分离** — 架构推荐、平台选型从 log_collect/script_gen 提取到 advisory 模块
- **前端路由更新** — 新增 `/advisory/arch` 和 `/advisory/platform` 路由
- **API 路径迁移** — 架构推荐 → `/api/v1/advisory/architecture/recommend`，平台选型 → `/api/v1/advisory/platform/choose`

### 变更文件

- `modules/advisory/` — 新增规划咨询模块（arch_strategy, platform_strategy, service, router, schemas）
- `app/main.py` — 注册 advisory 路由，版本号更新至 3.1.0
- `modules/log_collect/router.py` — 移除架构推荐路由
- `modules/log_collect/service.py` — 移除架构推荐方法
- `modules/script_gen/router.py` — 移除平台选型路由
- `modules/script_gen/service.py` — 移除平台选型方法
- `modules/script_gen/schemas.py` — 移除 PlatformChooseReq
- `app/schemas/log_collect.py` — 移除 ArchitectureRecommendReq
- `frontend/src/api.ts` — 新增 advisory API 组
- `frontend/src/App.vue` — 更新路由映射
- `frontend/src/config.ts` — 新增 advisory 模块配置
- `frontend/src/modules/compliance/Baseline.vue` — 新增基线报告下载功能
- `tests/test_rules/test_advisory.py` — 新增规划咨询模块测试
- `docs/dev_standard.md` — 更新模块描述

---

## [v3.0.0] - 2026-07-24

### 新增功能

- **安全威胁狩猎模块** — 日志联合审查升级为安全威胁狩猎，关键词 + LLM 双引擎驱动
- **多文件上传** — 支持同时上传多个日志文件进行关联分析
- **前端联动** — 威胁狩猎结果与前端实时联动展示

### 优化

- **LLM prompt 优化** — 精简关联分析 prompt，提升响应速度与准确性
- **攻击链检测规则** — 重写 correlation_patterns.json，覆盖更多攻击场景
- **Schema 扩展** — log_correlate schemas 新增多文件上传与威胁狩猎字段

### 修复

- **LLM JSON 截断恢复** — 4 层容错解析机制，确保不完整 JSON 不会崩溃
- **关联分析合并模式** — LLM + 关键词结果智能合并，避免重复告警

### 变更文件

- `modules/log_correlate/service.py` — 核心逻辑重构（+1028 行）
- `frontend/src/modules/log-correlate/Analyze.vue` — 前端联动改造
- `data/rule_data/correlation_patterns.json` — 攻击链规则重写
- `app/schemas/log_correlate.py` — Schema 扩展

---

## [v2.1.0] - 2026-07-24

### 优化

- **实训提交性能**：提交后分析 timeout 由 30s 降至 15s，prompt 精简，A 级任务跳过 LLM 直接出报告
- **日志识别页面**：支持多行输入，逐条分别识别
- **批量解析**：结果增加风险说明、攻击类型、处置建议
- **实训报告**：低分任务可展开查看标准答案、解析说明、答题提示
- **提交校验**：Submit.vue 答题区必填校验 — 三题全填才能提交

### 修复

- 修复 3 个导致提交崩溃与报告为空的 bug
- 修复答案解析显示、报告生成、场景ID硬编码三大问题
- 修复 LLM 分析不工作问题
- 修复 8 个前端页面缺失字段展示
- Assess/Parse 页面支持 hashchange 重新激活时自动填充

### 改进

- 重构日志识别-解析-研判三个页面，打通完整分析链路

---

## [v2.0.0] - 2026-07-22

### 新增功能

#### 前端

- 新增 Vue3 + Vite + Element Plus 前端框架
- 新增日志联合审查模块（攻击链检测）
- 新增批量解析功能
- 新增 CLI 下载横幅与 GitHub Actions 自动打包发布
- 前端响应式设计与 UI 交互优化

#### 后端

- RAG 知识库数据导入（ChromaDB）
- compliance 模块接入 RAG 知识库检索 + LLM 智能解读
- 合规问答添加大模型兜底功能
- 关联分析攻击链检测规则优化
- 向量库嵌入能力增强，支持多级降级策略
- 故障诊断混合架构 — 关键词匹配 + LLM 降级

#### CLI

- CLI v2.1 — 自然语言输出、格式化器重写、移除实训模块
- 新增联合日志审查模块
- 合规问答匹配改进 + 通用日志解析器

### 修复

- 修复审计发现的 10 个 bug
- 彻底解决 ChromaDB 测试超时问题
- 修复日志解析与风险研判多项问题
- 修复前端静态资源 404、滚动问题、风险等级映射
- 正则生成场景识别同时考虑日志样本内容

### 重构

- 删除废弃的 static 前端目录，统一使用 Vite 构建
- 重构日志联合审查攻击链检测逻辑，改用关键词匹配模式
- 重构 API 调用参数顺序

---

## [v1.0.0] - 2026-07-18

### 新增功能

#### 核心模块

- **模块一：日志解析** — 支持 SSH / Web / WAF / Firewall / DB 五类日志识别与结构化解析
- **模块二：日志采集架构指导** — 设备协议匹配、故障知识库、采集模板推荐
- **模块三：脚本生成** — 基于设备类型和日志格式自动生成采集脚本
- **模块四：故障诊断** — 混合诊断架构，关键词匹配优先 + LLM 智能降级
- **模块五：攻防实训** — 交互式实训场景与评分体系

#### 工程能力

- 工厂注册模式，禁止内部硬编码实例化策略
- Pydantic v2 数据校验
- 外部化配置，映射表/阈值/故障库统一放 settings 或 data/rule_data
- 通用工具复用 common 模块

### 代码规范

- 全项目代码规范统一
- 模块间禁止互相 import，跨模块数据走 core 上下文
- 新增场景仅新增策略文件，不修改原有核心代码

---

## 版本说明

| 版本 | 发布日期 | 主要变更 |
|------|----------|----------|
| v3.2.0 | 2026-08-04 | Splunk/ES 实际执行接入、CLI 连接命令、攻击链转实训、script-gen 四大增强 |
| v3.1.0 | 2026-07-25 | 规划咨询模块、基线报告下载、模块职责分离 |
| v3.0.0 | 2026-07-24 | 安全威胁狩猎模块、多文件关联分析、LLM 容错 |
| v2.1.0 | 2026-07-24 | 性能优化、交互完善、bug 修复 |
| v2.0.0 | 2026-07-22 | Vue3 前端 + RAG 知识库 + CLI 工具 |
| v1.0.0 | 2026-07-18 | 五大核心模块基础架构 |
