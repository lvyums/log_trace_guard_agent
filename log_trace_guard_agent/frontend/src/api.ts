import type { ApiResponse } from './types'

const BASE = ''

async function request<T = any>(
  method: string,
  url: string,
  data?: any,
  options?: RequestInit,
): Promise<ApiResponse<T>> {
  const config: RequestInit = {
    method,
    headers: { 'Content-Type': 'application/json' },
    ...options,
  }

  if (data && method !== 'GET') {
    if (data instanceof FormData) {
      const headers = { ...config.headers as Record<string, string> }
      delete headers['Content-Type']
      config.headers = headers
      config.body = data
    } else {
      config.body = JSON.stringify(data)
    }
  }

  try {
    const resp = await fetch(BASE + url, config)
    if (!resp.ok) {
      return { success: false, data: null, msg: 'HTTP ' + resp.status }
    }
    const json = await resp.json()
    if (json.code === 0 || json.code === 200) {
      return { success: true, data: json.data, msg: json.msg }
    }
    return { success: false, data: null, msg: json.msg || 'request failed' }
  } catch (err: any) {
    return { success: false, data: null, msg: 'Network error: ' + err.message }
  }
}

export const Api = {
  get<T = any>(url: string, params?: Record<string, string>) {
    const query = params ? '?' + new URLSearchParams(params).toString() : ''
    return request<T>('GET', url + query)
  },
  post<T = any>(url: string, data?: any) {
    return request<T>('POST', url, data)
  },
  upload<T = any>(url: string, formData: FormData) {
    return request<T>('POST', url, formData)
  },

  logParse: {
    identify: (data: any) => request('/api/v1/log-parse/identify', 'POST', data),
    parse: (data: any) => request('/api/v1/log-parse/parse', 'POST', data),
    assess: (data: any) => request('/api/v1/log-parse/assess', 'POST', data),
    batch: (data: any) => request('/api/v1/log-parse/parse/batch', 'POST', data),
  },
  logCollect: {
    match: (data: any) => request('/api/v1/log-collect/match', 'POST', data),
    plan: (data: any) => request('/api/v1/log-collect/plan', 'POST', data),
    fault: (data: any) => request('/api/v1/log-collect/fault/diagnose', 'POST', data),
    arch: (data: any) => request('/api/v1/log-collect/architecture/recommend', 'POST', data),
  },
  scriptGen: {
    regex: (data: any) => request('/api/v1/script-gen/regex', 'POST', data),
    esQuery: (data: any) => request('/api/v1/script-gen/es-query', 'POST', data),
    platform: (data: any) => request('/api/v1/script-gen/platform', 'POST', data),
    trace: (data: any) => request('/api/v1/script-gen/trace', 'POST', data),
    optimize: (data: any) => request('/api/v1/script-gen/optimize', 'POST', data),
  },
  compliance: {
    qa: (data: any) => request('/api/v1/compliance/qa', 'POST', data),
    baseline: (data: any) => request('/api/v1/compliance/baseline', 'POST', data),
    check: (data: any) => request('/api/v1/compliance/check', 'POST', data),
  },
  training: {
    scenarios: () => request('/api/v1/training/dispatch', 'POST', { scenario_id: '', category: '' }),
    submit: (data: any) => request('/api/v1/training/submit', 'POST', data),
    report: (data: any) => request('/api/v1/training/report', 'POST', data),
  },
}
