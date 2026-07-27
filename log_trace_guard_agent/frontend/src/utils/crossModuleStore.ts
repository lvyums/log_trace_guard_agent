/**
 * 跨模块共享状态 — 让组件间传递数据
 *
 * 用法：
 *   // Trace.vue 写数据并导航
 *   sendToCorrelate({ logs: [...], source: 'trace-splunk' })
 *   window.location.hash = '#/log-correlate/analyze'
 *
 *   // Analyze.vue 在 onMounted 中读取
 *   const data = consumeIncoming()
 *   if (data) { input.value = data.logs.join('\n'); submit() }
 */
import { reactive } from 'vue'

export interface CrossModuleData {
  logs: string[]
  source?: string
  chainName?: string
}

const store = reactive<{ incoming: CrossModuleData | null }>({
  incoming: null,
})

export function sendToCorrelate(data: CrossModuleData) {
  store.incoming = data
}

export function consumeIncoming(): CrossModuleData | null {
  const data = store.incoming
  store.incoming = null
  return data
}

export { store }
