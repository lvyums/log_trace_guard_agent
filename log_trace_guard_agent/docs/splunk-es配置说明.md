# Splunk & Elasticsearch 集成配置说明

> 适用版本：v3.0+
> 更新时间：2026-07-28

---

## 一、功能概述

| 功能 | Web 端（后端 API） | CLI 端（log-guard） | 说明 |
|------|:---:|:---:|------|
| **Splunk 搜索执行** | ✅ | ✅ | 提交 SPL → 轮询结果 → 返回事件 |
| **Splunk 连接测试** | ✅ | ✅ | 执行 `search index=_internal \| head 1` |
| **Splunk 跳转链接** | ✅ | ❌ | 生成 Splunk Web UI 打开链接 |
| **Splunk SPL 生成** | ✅ (AI生成) | ✅ (AI生成) | 由 LLM 按场景生成 SPL 语句 |
| **ES 查询生成** | ✅ (AI生成DSL) | ✅ (AI生成DSL) | 由 LLM 按场景生成 ES Query DSL JSON |
| **ES 查询执行** | ✅ (新) | ✅ | Web 端新增 ES 客户端，可直接向 ES 集群发送查询 |
| **ES 模板管理** | ❌ | ✅ | CLI 端保存/加载/删除命名模板 |
| **溯源→ES/Splunk** | ✅ | ✅ | 攻击溯源结果一键转为 ES DSL / SPL |

> 2026-07-28 更新：Web 端新增 `common/es_client.py` 和 ES 配置面板，现在 Web 端也可以**实际执行 ES 查询**，不再仅限于生成 DSL。

---

## 二、Splunk 配置

### 2.1 Web 端配置（前后端两种方式）

#### 方式 A：通过前端 UI 配置（推荐）

1. 登录系统后，点击右上角 **系统设置**（齿轮图标）
2. 切换到 **Splunk** Tab
3. 填写：

| 字段 | 示例 | 说明 |
|------|------|------|
| Splunk URL | `https://splunk.company.com:8089` | Splunk REST API 地址（**非 Web UI**，端口通常是 8089） |
| 认证方式 | Token / 用户名密码 | 二选一 |
| Auth Token | `Bearer eyJhbGciOiJSUzI1Ni...` | Token 认证时的 Bearer Token |
| 用户名 | `admin` | Basic 认证时使用 |
| 密码 | `***` | Basic 认证时使用 |
| 最大返回条数 | `100` | 每次搜索最多返回多少条 |
| 验证 SSL | ✅ | 是否校验 SSL 证书（自签名证书可取消勾选） |

4. 点击 **测试连接** 验证连通性
5. 点击 **保存**

> ⚠️ 前端配置保存在浏览器 `localStorage`（key: `lg-splunk-config`），每次调用 Splunk API 时携带到后端。更换浏览器或清除缓存后需要重新配置。

#### 方式 B：通过后端环境变量配置（全局生效）

在项目根目录的 `.env` 文件中设置：

```env
# ── Splunk 配置 ──
SPLUNK_BASE_URL=https://splunk.company.com
SPLUNK_USERNAME=admin
SPLUNK_PASSWORD=your_password
# SPLUNK_AUTH_TOKEN=your_token     # Token 认证时用（优先于用户名密码）
SPLUNK_VERIFY_SSL=true
SPLUNK_SEARCH_TIMEOUT=30
SPLUNK_MAX_RESULTS=100
```

配置后重启后端服务即可生效。这种方式下所有用户共享同一套 Splunk 配置。

#### 两种方式的优先级

1. 前端请求体中的 `splunk_config`（localStorage 传入）> 2. 后端 `.env` 环境变量

### 2.2 CLI 端配置

运行 `log-guard`，在主菜单中选择 **1. 选择日志文件**（或其他任意菜单），然后进入 **连接配置 > 2. Splunk 连接**：

```
======== 连接配置 ========
1. ES 集群连接
2. Splunk 连接
请选择 (1-2, 输入Enter返回主菜单):
```

选择 2 后：

```
======== Splunk 连接管理 ========
1. 配置 Splunk 连接
2. 查看当前配置
3. 清除配置
请选择 (1-3, 输入Enter返回):
```

选择 1，依次输入：

| 提示 | 示例 | 说明 |
|------|------|------|
| Splunk 主机地址 | `192.168.1.100` | IP 或域名 |
| 端口 | `8089` | Splunk REST API 端口（**不是** Web UI 的 8000） |
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

### 2.3 Splunk 使用流程

#### Web 端

1. **攻击溯源** → 在溯源结果页查看 SPL 脚本 → 点击 **"执行查询"** → 结果在表格中展示 → 可点击 **"在 Splunk 中打开"** 跳转 Web UI → 可点击 **"送到关联分析"** 回流到关联分析模块
2. **脚本生成** → 选择 **SPL 生成** → 输入场景描述 → AI 生成 SPL

#### CLI 端

1. 主菜单 → **脚本生成 → 2. Splunk SPL生成** → AI 按场景生成 SPL
2. 主菜单 → **脚本生成 → 6. Splunk SPL生成+执行** → 选择 5 个内置场景之一 → AI 生成 SPL → 自动发送到 Splunk 执行

---

## 三、Elasticsearch 配置

### 3.1 Web 端配置

系统设置弹窗中新增 **Elasticsearch** Tab，支持两种保存方式：

| 操作 | 按钮 | 说明 |
|------|------|------|
| **临时保存** | 临时保存 | 保存到浏览器 localStorage，每次请求携带到后端。重启浏览器/清除缓存后需重新配置 |
| **永久保存** | 保存到 .env | 通过 API 写入后端 `.env` 文件。重启后端服务后永久生效，所有用户共享 |
| **测试连接** | 测试连接 | 向后端 ES 客户端发送 `/` 请求，返回集群名称和版本号 |

#### 配置字段

| 字段 | 示例 | 说明 |
|------|------|------|
| ES URL | `http://localhost:9200` | ES REST API 地址（**不是** Kibana 的 5601） |
| 用户名 | `elastic` | 可选，ES 有安全认证时填写 |
| 密码 | `***` | 可选 |
| 最大返回条数 | `100` | 每次搜索最多返回多少条（最大 10000） |
| 验证 SSL | ✅ | 自签名证书可取消勾选 |

#### 配置步骤

1. 点击右上角 **系统设置** → 切换到 **Elasticsearch** Tab
2. 填写 ES URL 和认证信息
3. 点击 **测试连接** 验证连通性
4. 点击 **临时保存**（仅当前浏览器生效）或 **保存到 .env**（全局永久生效）
5. 如果选择保存到 .env，重启后端服务后生效

### 3.2 Web 端 ES 使用流程

**新增** 溯源页面支持直接执行 ES 查询：

1. **攻击溯源** → 溯源结果包含 ES Query DSL → 点击 **"ES 执行"** → 结果在表格中展示
2. **脚本生成 → ES 查询生成** → 输入场景 → 得到 DSL JSON → 点击 **"执行查询"** 向已配置的 ES 集群发请求

### 3.3 CLI 端配置

CLI 端支持 **实际向 ES 集群发送查询**，需要配置连接。

运行 `log-guard` → **连接配置 > 1. ES 集群连接**：

```
======== ES 集群连接管理 ========
1. 配置 ES 连接
2. 查看当前配置
3. 清除配置
请选择 (1-3, 输入Enter返回):
```

选择 1，依次输入：

| 提示 | 示例 | 说明 |
|------|------|------|
| ES 主机地址 | `localhost` | IP 或域名（默认 localhost） |
| 端口 | `9200` | ES HTTP 端口（默认 9200） |
| 协议 | `http` | http 或 https |
| 用户名 | `elastic` | 有安全认证时填写（可选） |
| 密码 | `***` | 有安全认证时填写（可选） |

配置保存在 `~/.log-guard/config.json`：

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

### 3.4 CLI 端 ES 使用流程

1. **脚本生成 → 1. ES查询生成** → 按场景生成 DSL → 可选择执行
2. **脚本生成 → 2. ES查询模板管理** → 管理已保存的命名模板
3. **攻击溯源 → 溯源报告导出** → 自动生成 ES DSL

---

## 四、配置文件速查

### 4.1 `.env`（后端 Web 服务）

```env
# ── Splunk 配置（可选） ──
SPLUNK_BASE_URL=https://splunk.company.com:8089
SPLUNK_USERNAME=admin
SPLUNK_PASSWORD=your_password
SPLUNK_AUTH_TOKEN=your_token          # 优先于用户名密码
SPLUNK_VERIFY_SSL=true
SPLUNK_SEARCH_TIMEOUT=30
SPLUNK_MAX_RESULTS=100

# ── ES 配置（可选） ──
ES_BASE_URL=http://localhost:9200
ES_USERNAME=elastic
ES_PASSWORD=your_password
ES_VERIFY_SSL=true
ES_SEARCH_TIMEOUT=30
ES_MAX_RESULTS=100
```

### 4.2 `~/.log-guard/config.json`（CLI 端）

```json
{
  "elasticsearch": {
    "host": "localhost",
    "port": 9200,
    "scheme": "http",
    "user": "",
    "password": ""
  },
  "splunk": {
    "host": "192.168.1.100",
    "port": 8089,
    "scheme": "https",
    "user": "admin",
    "password": "your_password"
  }
}
```

### 4.3 前端 localStorage（浏览器）

| Key | 内容 | 说明 |
|-----|------|------|
| `lg-splunk-config` | `{base_url, auth_mode, auth_token?, username?, password?, verify_ssl, max_results}` | Splunk 连接配置 |
| `lg-es-config` | `{base_url, username?, password?, verify_ssl, max_results}` | ES 连接配置 |
| `lg-app-config` | `{api_key, base_url, model_name}` | AI 模型配置 |

---

## 五、API 端点速查

| 方法 | 路径 | 功能 | 说明 |
|------|------|------|------|
| POST | `/api/v1/script-gen/splunk/search` | Splunk 搜索执行 | 需 Splunk 配置 |
| POST | `/api/v1/script-gen/splunk/open-url` | 生成 Splunk Web UI 链接 | 需 Splunk 配置 |
| POST | `/api/v1/script-gen/splunk/test` | 测试 Splunk 连接 | 需 Splunk 配置 |
| POST | `/api/v1/script-gen/es/search` | ES 搜索执行 | 需 ES 配置（**新增**） |
| POST | `/api/v1/script-gen/es/test` | 测试 ES 连接 | 需 ES 配置（**新增**） |
| POST | `/api/v1/script-gen/es/config` | 保存 ES 配置到 .env | 管理员操作（**新增**） |
| POST | `/api/v1/script-gen/es-query` | 生成 ES DSL（不执行） | 纯 AI 生成 |
| POST | `/api/v1/script-gen/trace` | 攻击溯源 | 自动生成 ES/Splunk 脚本 |

---

## 六、常见问题

### Q1: Splunk 连接测试失败

- **确认端口**：Splunk REST API 默认端口是 **8089**，不是 Web UI 的 8000
- **确认认证方式**：Splunk 的 Bearer Token 无需手动加前缀，SDK 自动加 `Splunk ` 前缀
- **自签名证书**：取消勾选「验证 SSL 证书」
- **网络可达**：确保后端服务器（Web）/ 本机（CLI）能与 Splunk 服务器通信

### Q2: ES 查询生成后怎么执行？

- **Web 端**：现在可以直接执行！在溯源页或 ES 查询生成页，点击 **"执行查询"** 即可向已配置的 ES 集群发送 DSL 并返回结果
- **CLI 端**：ES 查询生成后自动提示是否要执行

### Q3: 前端配置的 Splunk/ES 信息安全吗？

前端配置保存在浏览器 `localStorage`，每次请求发到后端。如果担心安全问题：
1. 使用 **保存到 .env** 方式（ES 的「保存到 .env」按钮会通过 API 写入后端文件）
2. 或在 `.env` 中直接配置，前端不保存敏感信息

### Q4: ES 查询支持哪些场景？

内置 5 大场景，Web 端支持任意自然语言输入：

| 场景 | 说明 |
|------|------|
| SSH 爆破检测 | 搜索失败登录和频率异常 |
| SQL 注入检测 | 搜索 SQL 关键字和异常参数 |
| Web 攻击检测 | 搜索路径遍历、XSS、命令注入等 |
| 异常流量检测 | 搜索流量突增、非工作时间请求等 |
| 数据泄露检测 | 搜索敏感信息外传、大体积响应等 |

### Q5: 端口混淆提醒

| 服务 | REST API 端口 | Web UI 端口 |
|------|:-:|:-:|
| **Splunk** | **8089** | 8000 |
| **Elasticsearch** | **9200** | 5601 (Kibana) |

配置时请确认使用的是 **API 端口**，而非 Web UI 端口。

### Q6: 保存到 .env 后需要重启吗？

**需要**。保存到 `.env` 后，后端服务需要重启才能读取新的环境变量。但前端 localStorage 中的配置不受重启影响，重启前仍可使用临时配置。
