# 日志溯源卫士智能体 v3.0 — 前端开发指南

## 开发模式

```bash
# 1. 启动后端
cd log_trace_guard_agent
python -m app.main

# 2. 启动前端开发服务器（新终端）
cd log_trace_guard_agent/frontend
npm run dev
# → http://localhost:5173 自动代理 /api 到 :8000
```

## 生产构建

```bash
cd log_trace_guard_agent/frontend
npm run build
# → 产出在 frontend/dist/，FastAPI 自动优先使用
```

## 项目结构

```
frontend/
├── index.html              # Vite 入口
├── package.json            # 依赖和脚本
├── vite.config.ts          # Vite 配置（代理、别名、构建）
├── tsconfig.json           # TypeScript 配置
├── env.d.ts                # 类型声明
├── src/
│   ├── main.ts             # 应用入口（注册 Element Plus + 图标）
│   ├── App.vue             # 根组件（导航 + 路由）
│   ├── config.ts           # 全局配置 + 风险等级工具 + 模块定义
│   ├── api.ts              # API 请求层
│   ├── utils.ts            # 通用工具函数
│   ├── types.ts            # TypeScript 类型定义
│   ├── css/                # 样式文件
│   ├── components/         # 可复用组件（.vue SFC）
│   │   ├── GlobalTour.vue  # 新手引导
│   │   ├── AlertGuide.vue  # 操作提示条
│   │   ├── EmptyGuide.vue  # 空状态
│   │   ├── ResultGuide.vue # 结果解读
│   │   ├── RiskBadge.vue   # 风险等级标签
│   │   ├── RiskCard.vue    # 风险研判卡片
│   │   ├── CodeBlock.vue   # 代码展示
│   │   ├── KnowledgePanel.vue # 知识点面板
│   │   ├── ConfirmBatch.vue # 批量确认弹窗
│   │   └── CliDownloadBanner.vue # CLI下载横幅
│   └── modules/            # 页面组件（按模块分组）
│       ├── log-parse/      # 日志解析（4个页面）
│       ├── log-correlate/  # 日志联合审查（2个页面）
│       ├── advisory/       # 规划咨询（4个页面）
│       ├── log-collect/    # 故障诊断（13个页面，含采集方案子功能）
│       ├── script-gen/     # 脚本生成（4个页面）
│       ├── compliance/     # 合规审计（3个页面）
│       └── training/       # 攻防实训（2个页面）
└── dist/                   # 构建产出（gitignored）
```

## 导航模块

前端配置定义在 `src/config.ts` 的 `APP_CONFIG.modules` 数组中，共 **7 个模块、22 个子页面**：

| 模块 key         | 导航名       | 子页面数 | 路由前缀                      |
| ---------------- | ------------ | -------- | ----------------------------- |
| `log-parse`      | 日志解析     | 4        | `/log-parse/`                 |
| `log-correlate`  | 日志联合审查 | 2        | `/log-correlate/`             |
| `advisory`       | 规划咨询     | 4        | `/advisory/`                  |
| `fault`          | 故障诊断     | 1        | `/fault/`                     |
| `script-gen`     | 脚本生成     | 4        | `/script-gen/`                |
| `compliance`     | 合规审计     | 3        | `/compliance/`                |
| `training`       | 攻防实训     | 2        | `/training/`（仅实训模式显示） |

> 模块列表和路由映射在 `App.vue` 的 `ROUTE_MAP` 中定义。

## 迁移指南（CDN → Vite）

| 旧方式 | 新方式 |
|---|---|
| `var APP_CONFIG = {...}` | `export const APP_CONFIG = {...}` (config.ts) |
| `var Api = {...}` | `export const Api = {...}` (api.ts) |
| `const Comp = { template: '...' }` | `Comp.vue` SFC 文件 |
| `<script src="...">` | `npm install` + `import` |
| `ElementPlusElMessage` | `import { ElMessage } from 'element-plus'` |
| `var Utils = {...}` | `export const Utils = {...}` (utils.ts) |

## 新增页面组件

1. 在 `src/modules/<module>/` 下创建 `.vue` 文件
2. 在 `src/App.vue` 中：
   - `import` 新组件
   - 在 `ROUTE_MAP` 中添加路由映射
3. 在 `src/config.ts` 的 `APP_CONFIG.modules` 中注册模块/子页面
4. `npm run build` 验证
