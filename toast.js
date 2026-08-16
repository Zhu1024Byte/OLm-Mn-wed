import { reactive } from 'vue'

/**
 * Minimal global toast bus — no Pinia store needed.
 * Usage: import { toast } from '@/utils/toast'; toast('已保存', 'success')
 */
export const toasts = reactive([])

let seq = 0

export function toast(message, type = 'info', duration = 4000) {
  const id = ++seq
  toasts.push({ id, message, type })
  setTimeout(() => {
    const i = toasts.findIndex((t) => t.id === id)
    if (i >= 0) toasts.splice(i, 1)
  }, duration)
}
