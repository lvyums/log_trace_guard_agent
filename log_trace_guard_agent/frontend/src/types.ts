/** 风险等级定义 */
export interface RiskLevelDef {
  label: string
  color: string
  bg: string
  icon: string
}

/** 模块子项 */
export interface ModuleChild {
  path: string
  label: string
  icon: string
  tip: string
}

/** 模块定义 */
export interface ModuleDef {
  key: string
  label: string
  icon: string
  desc: string
  children: ModuleChild[]
}

/** 引导步骤 */
export interface GuideStep {
  title: string
  desc: string
}

/** 结果指引 */
export interface ResultGuides {
  [key: string]: string
}

/** 模块提示 */
export interface ModuleTip {
  type: 'info' | 'warning' | 'danger' | 'success'
  title: string
  content: string
}

/** 空状态 */
export interface EmptyState {
  title: string
  desc: string
  action: string
  hint: string
}

/** 工具提示 */
export interface TooltipDef {
  label: string
  desc: string
  example: string
}

/** API 响应 */
export interface ApiResponse<T = any> {
  success: boolean
  data: T | null
  msg: string
}

/** 风险等级映射 */
export type RiskLevelKey = 'P0' | 'P1' | 'P2' | 'P3' | 'normal'

/** 模块路由映射：path → component 名 */
export type RouteMap = Record<string, string>
