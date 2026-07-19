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
    identify: (data: any) => request('POST', '/api/v1/log-parse/identify', data),
    parse: (data: any) => request('POST', '/api/v1/log-parse/parse', data),
    assess: (data: any) => request('POST', '/api/v1/log-parse/assess', data),
    batch: (data: any) => request('POST', '/api/v1/log-parse/parse/batch', data),
  },
  logCollect: {
    match: (data: any) => request('POST', '/api/v1/log-collect/match', data),
    plan: (data: any) => request('POST', '/api/v1/log-collect/plan', data),
    fault: (data: any) => request('POST', '/api/v1/log-collect/fault/diagnose', data),
    arch: (data: any) => request('POST', '/api/v1/log-collect/architecture/recommend', data),
  },
  scriptGen: {
    regex: (data: any) => request('POST', '/api/v1/script-gen/regex', data),
    esQuery: (data: any) => request('POST', '/api/v1/script-gen/es-query', data),
    platform: (data: any) => request('POST', '/api/v1/script-gen/platform', data),
    trace: (data: any) => request('POST', '/api/v1/script-gen/trace', data),
    optimize: (data: any) => request('POST', '/api/v1/script-gen/optimize', data),
  },
  compliance: {
    qa: (data: any) => request('POST', '/api/v1/compliance/qa', data),
    baseline: (data: any) => request('POST', '/api/v1/compliance/baseline', data),
    check: (data: any) => request('POST', '/api/v1/compliance/check', data),
  },
  logCorrelate: {
    correlate: (data: any) => request('POST', '/api/v1/log-correlate/correlate', data),
    patterns: () => request('GET', '/api/v1/log-correlate/patterns'),
  },
  training: {
    scenarios: () => request('POST', '/api/v1/training/dispatch', { scenario_id: '', category: '' }),
    submit: (data: any) => request('POST', '/api/v1/training/submit', data),
    report: (data: any) => request('POST', '/api/v1/training/report', data),

    /**
     * 流式分析：POST 后通过 SSE 逐 token 接收答案解析
     * @param data 与 submit 相同的请求参数
     * @param callbacks.onResult 评分结果回调 {score, grade, checks}
     * @param callbacks.onToken 每个 token 文本回调
     * @param callbacks.onDone 完成回调
     * @param callbacks.onError 错误回调
     */
    analyzeStream: async (
      data: any,
      callbacks: {
        onResult?: (result: { score: number; grade: string; checks: any[] }) => void
        onToken?: (text: string) => void
        onDone?: () => void
        onError?: (err: string) => void
      },
    ) => {
      try {
        const resp = await fetch(BASE + '/api/v1/training/analyze-stream', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        })
        if (!resp.ok || !resp.body) {
          callbacks.onError?.('HTTP ' + resp.status)
          return
        }

        const reader = resp.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''  // 保留未完成的行

          for (const line of lines) {
            const trimmed = line.trim()
            if (!trimmed.startsWith('data: ')) continue

            try {
              const event = JSON.parse(trimmed.slice(6))
              if (event.type === 'result') {
                callbacks.onResult?.(event)
              } else if (event.type === 'token') {
                callbacks.onToken?.(event.text)
              } else if (event.type === 'done') {
                callbacks.onDone?.()
              }
            } catch {
              // 忽略解析失败的行
            }
          }
        }
      } catch (err: any) {
        callbacks.onError?.('Network error: ' + err.message)
      }
    },
  },
}
