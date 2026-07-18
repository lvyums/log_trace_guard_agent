import { getRiskLevel } from './config'

export const Utils = {
  getRiskLevel,

  async copyText(text: string): Promise<boolean> {
    try {
      await navigator.clipboard.writeText(text)
      return true
    } catch {
      const ta = document.createElement('textarea')
      ta.value = text
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
      return true
    }
  },

  formatTime(date: Date | string | number): string {
    return new Date(date).toLocaleString('zh-CN', { hour12: false })
  },

  debounce<T extends (...args: any[]) => any>(fn: T, delay = 300): (...args: Parameters<T>) => void {
    let timer: ReturnType<typeof setTimeout> | null = null
    return (...args: Parameters<T>) => {
      if (timer) clearTimeout(timer)
      timer = setTimeout(() => fn(...args), delay)
    }
  },
}
