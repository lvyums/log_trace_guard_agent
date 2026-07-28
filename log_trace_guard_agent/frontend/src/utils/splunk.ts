const SPLUNK_KEY = 'lg-splunk-config'
const APP_KEY = 'lg-app-config'

// ── Splunk 配置 ──

export function getSplunkConfig() {
  try {
    const raw = localStorage.getItem(SPLUNK_KEY)
    if (raw) {
      const c = JSON.parse(raw)
      if (c.base_url) return {
        base_url: c.base_url,
        auth_token: c.auth_mode === 'token' ? c.auth_token : undefined,
        username: c.auth_mode === 'basic' ? c.username : undefined,
        password: c.auth_mode === 'basic' ? c.password : undefined,
        verify_ssl: c.verify_ssl,
      }
    }
  } catch {}
  return null
}

export function saveSplunkConfig(config: Record<string, any>) {
  localStorage.setItem(SPLUNK_KEY, JSON.stringify(config))
}

export function loadSplunkConfig() {
  try {
    const raw = localStorage.getItem(SPLUNK_KEY)
    if (raw) return JSON.parse(raw)
  } catch {}
  return null
}

// ── AI 配置 ──

export interface AiConfig {
  api_key: string
  base_url: string
  model_name: string
}

export function getAiConfig(): AiConfig | null {
  try {
    const raw = localStorage.getItem(APP_KEY)
    if (raw) {
      const c = JSON.parse(raw)
      if (c.api_key) return c
    }
  } catch {}
  return null
}

export function saveAiConfig(config: AiConfig) {
  localStorage.setItem(APP_KEY, JSON.stringify(config))
}

export function loadAiConfig(): AiConfig {
  try {
    const raw = localStorage.getItem(APP_KEY)
    if (raw) return JSON.parse(raw)
  } catch {}
  return { api_key: '', base_url: 'https://raytoken.com.cn/v1', model_name: 'deepseek-v4-flash' }
}

// ── ES 配置 ──

const ES_CONFIG_KEY = 'lg-es-config'

export interface EsConfig {
  base_url: string
  username?: string
  password?: string
  verify_ssl: boolean
  max_results: number
}

export function getEsConfig(): EsConfig | null {
  try {
    const raw = localStorage.getItem(ES_CONFIG_KEY)
    if (raw) {
      const c = JSON.parse(raw)
      if (c.base_url) return c
    }
  } catch {}
  return null
}

export function saveEsConfig(config: Record<string, any>) {
  localStorage.setItem(ES_CONFIG_KEY, JSON.stringify(config))
}

export function loadEsConfig(): EsConfig {
  try {
    const raw = localStorage.getItem(ES_CONFIG_KEY)
    if (raw) return JSON.parse(raw)
  } catch {}
  return esConfigDefaults()
}

export function esConfigDefaults(): EsConfig {
  return {
    base_url: '',
    username: '',
    password: '',
    verify_ssl: true,
    max_results: 100,
  }
}
