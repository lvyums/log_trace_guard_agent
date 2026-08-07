# Splunk & Elasticsearch 接入说明

> 适用版本：v3.0+（2026-08-04 更新）
> 覆盖：Web 端（FastAPI + Vue3 SPA）与 CLI 端（log-guard）

---

## 一、功能总览

接入 Splunk / ES 后，系统可以**实际执行查询**（不再只是生成脚本）：

| 功能 | Web 端 | CLI 端 | 说明 |
|------|:---:|:---:|------|
| **Splunk 搜索执行** | ✅ | ✅ | 提交 SPL → 轮询任务 → 返回事件 |
| **Splunk 连接测试** | ✅ | ✅ | 测试连接并返回命中数 |
| **Splunk 跳转链接** | ✅ | ❌ | 生成 Splunk Web UI 打开链接 |
| **Splunk 配置持久化到 .env** | ✅ | — | 前端「保存到 .env」按钮，全局生效 |
| **ES 搜索执行** | ✅ | ✅ | 发送 Query DSL → 返回命中文档 |
| **ES 连接测试** | ✅ | ✅ | 返回集群名 + 版本号 |
| **ES 配置持久化到 .env** | ✅ | — | 前端「保存到 .env」按钮，全局生效 |
| **SPL / DSL 生成** | ✅ (AI) | ✅ (AI) | 按场景生成 SPL 或 ES DSL |
| **溯源→ES/Splunk 一键执行** | ✅ | ✅ | 攻击溯源结果直接查库 |

> 2026-08-04 更新：
> - Splunk 新增「保存到 .env」按钮，与 ES 持久化方式对称（接口 `POST /splunk/config`）
> - CLI 新增命令行模式：`--splunk-test` / `--splunk-search` / `--es-test` / `--es-search`，可脚本集成
> - Splunk Bearer Token 自动兼容 `Bearer ` 前缀，粘贴带前缀的 Token 也不会出错
> - 前端脚本生成页（ES 查询生成）新增「执行查询」按钮，生成 DSL 后可直接查库

---

## 二、快速接入（5 分钟）

### Web 端

1. 启动系统，点击右上角 **系统设置**（齿轮图标）
2. 切到 **Splunk** 或 **Elasticsearch** Tab
3. 填写连接信息 → 点 **测试连接** 验证
4. 点 **临时保存**（仅当前浏览器）或 **保存到 .env**（全局永久生效，重启后端后生效）

### CLI 端

```bash
log-guard                     # 进入交互模式
# 主菜单 → 连接配置 → 1. ES 集群连接 / 2. Splunk 连接
# 按提示输入地址/端口/账号密码，保存后即可使用
```

或直接用命令行模式（适合脚本集成）：

```bash
log-guard --es-test --json                    # 测试 ES 连接
log-guard --splunk-search 'search index=* | head 5' --json   # 执行 SPL
```

---

## 三、Splunk 接入

### 3.1 Web 端 UI 配置（系统设置 → Splunk Tab）

| 字段 | 示例 | 说明 |
|------|------|------|
| Splunk URL | `https://splunk.company.com:8089` | **REST API 地址**（端口 8089，非 Web UI 的 8000） |
| 认证方式 | Token / 用户名密码 | 二选一 |
| Auth Token | `eyJhbGciOiJSUzI1Ni...` | Token 认证时填写，可带可不带 `Bearer ` 前缀 |
| 用户名 / 密码 | `admin` / `***` | Basic 认证时填写 |
| 最大返回条数 | `100` | 每次搜索最多返回条数（1–1000） |
| 验证 SSL 证书 | ✅ | 自签名证书环境请取消勾选 |

三个按钮：

| 按钮 | 行为 | 生效范围 |
|------|------|------|
| **测试连接** | 执行 `search index=_internal \| head 1` | 即时 |
| **临时保存** | 写入浏览器 localStorage（key: `lg-splunk-config`） | 仅当前浏览器，每次请求携带到后端 |
| **保存到 .env** | 通过 `POST /splunk/config` 写入后端 `.env` | 全局共享，**重启后端后生效** |

### 3.2 后端 .env 配置（全局生效，免前端配置）

在项目根目录 `.env` 中设置：

```env
# ── Splunk 配置 ──
SPLUNK_BASE_URL=https://splunk.company.com:8089
SPLUNK_USERNAME=admin
SPLUNK_PASSWORD=your_password
# SPLUNK_AUTH_TOKEN=your_token     # Token 认证时用（优先于用户名密码）
SPLUNK_VERIFY_SSL=true
SPLUNK_SEARCH_TIMEOUT=30
SPLUNK_MAX_RESULTS=100
```

配置后重启后端服务生效。所有用户共享这一套配置。

### 3.3 CLI 交互式配置

```text
======== 连接配置 ========
1. ES 集群连接
2. Splunk 连接
请选择 (1-2, 输入Enter返回主菜单):
```

选 2 后：

```text
======== Splunk 连接管理 ========
1. 配置 Splunk 连接
2. 查看当前配置
3. 清除配置
```

| 提示 | 示例 | 说明 |
|------|------|------|
| Splunk 主机地址 | `192.168.1.100` | IP 或域名 |
| 端口 | `8089` | REST API 端口（**不是** Web UI 的 8000） |
| 协议 | `https` | http 或 https |
| 用户名 | `admin` | |
| 密码 | `***` | |

配置保存在 `~/.log-guard/config.json`：

```json
{
  "splunk": {
    "host": "192.168.1.100",
    "port": 8089,
    "scheme": "https",
    "user": "admin",
    "password": "..."
  }
}
```

### 3.4 CLI 命令行模式（脚本可集成）

| 命令 | 说明 | 退出码 |
|------|------|:---:|
| `log-guard --splunk-test` | 测试连接（执行 `search index=* \| head 1`） | 成功 0 / 失败 1 |
| `log-guard --splunk-search '<SPL>'` | 执行 SPL 搜索 | 成功 0 / 失败 1 |
| 任一命令加 `--json` | 结构化 JSON 输出 | — |

示例：

```bash
log-guard --splunk-test --json
# {"success": true, "event_count": 1, ...}

log-guard --splunk-search 'search index=* | head 5' --json
```

### 3.5 认证细节

- **Token 认证**：后端自动处理请求头。若 Token 以 `bearer ` 开头则原样使用，否则自动补 `Bearer ` 前缀——两种粘贴方式都不会出错。
- **Basic 认证**：用户名 + 密码，走 HTTP Basic Auth。
- **Token 优先于用户名密码**：同时提供时只用 Token。

---

## 四、Elasticsearch 接入

### 4.1 Web 端 UI 配置（系统设置 → Elasticsearch Tab）

| 字段 | 示例 | 说明 |
|------|------|------|
| ES URL | `http://localhost:9200` | **REST API 地址**（端口 9200，非 Kibana 的 5601） |
| 用户名（可选） | `elastic` | ES 开启安全认证时填写 |
| 密码（可选） | `***` | |
| 最大返回条数 | `100` | 每次搜索最多返回条数（1–10000） |
| 验证 SSL 证书 | ✅ | 自签名证书环境请取消勾选 |

按钮与 Splunk 对称：

| 按钮 | 行为 | 生效范围 |
|------|------|------|
| **测试连接** | 向后端发 `GET /`，返回**集群名 + 版本号** | 即时 |
| **临时保存** | 写入浏览器 localStorage（key: `lg-es-config`） | 仅当前浏览器 |
| **保存到 .env** | 通过 `POST /es/config` 写入后端 `.env` | 全局共享，**重启后端后生效** |

### 4.2 后端 .env 配置

```env
# ── ES 配置 ──
ES_BASE_URL=http://localhost:9200
ES_USERNAME=elastic
ES_PASSWORD=your_password
ES_VERIFY_SSL=true
ES_SEARCH_TIMEOUT=30
ES_MAX_RESULTS=100
```

### 4.3 CLI 交互式配置

主菜单 → **连接配置 → 1. ES 集群连接**：

| 提示 | 示例 | 说明 |
|------|------|------|
| ES 主机地址 | `localhost` | IP 或域名 |
| 端口 | `9200` | ES HTTP 端口 |
| 协议 | `http` | http 或 https |
| 用户名（可选） | `elastic` | |
| 密码（可选） | `***` | |

保存在 `~/.log-guard/config.json`：

```json
{
  "elasticsearch": {
    "host": "localhost",
    "port": 9200,
    "scheme": "http",
    "user": "elastic",
    "password": "..."
  }
}
```

### 4.4 CLI 命令行模式

| 命令 | 说明 | 退出码 |
|------|------|:---:|
| `log-guard --es-test` | 测试连接（执行 match_all 查询） | 成功 0 / 失败 1 |
| `log-guard --es-search '<DSL JSON>'` | 执行 ES 搜索 | 成功 0 / 失败 1 / **DSL 非法 2** |
| 任一命令加 `--json` | 结构化 JSON 输出 | — |

示例：

```bash
log-guard --es-test --json
# {"success": true, "total": 1, ...}

log-guard --es-search '{"query":{"match_all":{}},"size":5}' --json
```

> `--es-search` 传入非法 JSON 时返回退出码 2，可据此在脚本中区分「连接失败」和「DSL 语法错误」。

---

## 五、配置优先级与持久化

### 5.1 优先级

```
前端请求体中的连接配置（localStorage 携带）  >  后端 .env 环境变量
```

即：浏览器里做了「临时保存」，则本次请求用它；没配过或已清除，则回落使用 `.env` 的全局配置。

### 5.2 三种持久化方式对比

| 方式 | 操作 | 生效范围 | 持久性 |
|------|------|------|------|
| 临时保存 | Web UI「临时保存」 | 当前浏览器 | 换浏览器/清缓存后失效 |
| 保存到 .env | Web UI「保存到 .env」 | 全局（所有用户） | 重启后端后永久生效 |
| CLI 配置 | CLI 连接配置菜单 | 当前机器 | 存在 `~/.log-guard/config.json` |

> 部署建议：
> - **单机/内网部署**：直接改 `.env` 最省事
> - **Docker 部署**：`.env` 写入容器后重启丢失，应通过 `docker-compose.yml` 的 `environment` 注入
> - **多分析师共享**：各用户「临时保存」自己的连接，互不干扰；管理员可用「保存到 .env」设默认值

### 5.3 前端 localStorage Key

| Key | 内容 |
|-----|------|
| `lg-splunk-config` | Splunk 连接配置（base_url / auth_mode / auth_token / username / password / verify_ssl / max_results） |
| `lg-es-config` | ES 连接配置（base_url / username / password / verify_ssl / max_results） |
| `lg-app-config` | AI 模型配置（api_key / base_url / model_name） |

---

## 六、接入后使用入口

### Web 端

1. **攻击溯源** → 溯源结果含 SPL / ES DSL → 点击 **「执行查询」/「ES 执行」** → 结果表格展示 → 可「在 Splunk 中打开」跳转 Web UI
2. **脚本生成 → ES 查询生成** → 输入场景 → AI 生成 DSL → 点击 **「执行查询」** 直接查库（需已配置 ES）

### CLI 端

1. 主菜单 → **脚本生成** → SPL 生成 / ES 查询生成 / SPL 生成+执行（5 大内置场景）
2. 主菜单 → **攻击溯源** → 溯源报告导出（Markdown/JSON，自动附带 SPL / DSL）
3. 命令行模式：`--splunk-search` / `--es-search`（见 3.4 / 4.4）

---

## 七、API 端点速查

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/api/v1/script-gen/splunk/search` | Splunk 搜索执行 |
| POST | `/api/v1/script-gen/splunk/open-url` | 生成 Splunk Web UI 链接 |
| POST | `/api/v1/script-gen/splunk/test` | 测试 Splunk 连接 |
| POST | `/api/v1/script-gen/splunk/config` | 保存 Splunk 配置到 .env |
| POST | `/api/v1/script-gen/es/search` | ES 搜索执行 |
| POST | `/api/v1/script-gen/es/test` | 测试 ES 连接（返回集群名/版本） |
| POST | `/api/v1/script-gen/es/config` | 保存 ES 配置到 .env |
| POST | `/api/v1/script-gen/es-query` | AI 生成 ES DSL（不执行） |
| POST | `/api/v1/script-gen/trace` | 攻击溯源（自动生成 ES/Splunk 脚本） |

> 测试连接接口（`/splunk/test`、`/es/test`）的查询字段可留空，前端传空查询即可。

---

## 八、接入验证（本地联调环境）

仓库内置 mock 服务，无真实 Splunk/ES 也能验证整条链路：

```bash
# 1. 启动 mock（mock Splunk :18089 + mock ES :19200）
python scripts/dev/mock_services.py &

# 2. 后端联调回归（18 项：测试+搜索+配置保存）
python scripts/dev/test_api_connect.py

# 3. CLI 联调回归（16 项：退出码契约+连通性+JSON 输出）
python scripts/dev/test_cli_connect.py
```

联调回归脚本会自动清理 `.env` 改动并 reload 后端配置，可反复运行。

---

## 九、常见问题

### Q1: 连接测试失败？

- **端口确认**：Splunk REST API = **8089**（不是 Web UI 8000）；ES = **9200**（不是 Kibana 5601）
- **认证方式**：Splunk Token 走 Bearer（前缀自动兼容），Basic 走用户名密码
- **自签名证书**：取消勾选「验证 SSL 证书」
- **网络可达**：确保后端服务器（Web）/ 本机（CLI）与目标服务器互通

### Q2: 前端配置安全吗？

前端「临时保存」的凭据在浏览器 localStorage。敏感环境建议：
1. 用「保存到 .env」让配置留在后端，前端不存凭据
2. 或直接改后端 `.env`，前端完全不接触

### Q3: 保存到 .env 后需要重启吗？

**需要**。`SPLUNK_*` / `ES_*` 环境变量在服务启动时读取，保存后重启后端生效。重启前，已「临时保存」的浏览器配置不受影响。

### Q4: Docker 部署能用「保存到 .env」吗？

**不建议**。容器内 `.env` 在重建后丢失。应在 `docker-compose.yml` 的 `environment` 中注入 `SPLUNK_*` / `ES_*` 变量。

### Q5: 支持哪些查询场景？

内置 5 大场景（Web/CLI 通用）：SSH 爆破检测、SQL 注入检测、Web 攻击检测、异常流量检测、数据泄露检测；Web 端还支持任意自然语言描述生成 SPL/DSL。

### Q6: 命令行退出码含义？

| 退出码 | 含义 |
|:---:|------|
| 0 | 成功 |
| 1 | 连接失败 / 查询失败 |
| 2 | 仅 `--es-search`：DSL JSON 解析失败 |
