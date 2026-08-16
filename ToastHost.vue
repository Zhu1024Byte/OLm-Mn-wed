<template>
  <div class="toast-host">
    <transition-group name="toast">
      <div
        v-for="t in toasts"
        :key="t.id"
        class="toast"
        :class="t.type"
        @click="dismiss(t.id)"
      >
        <span class="toast-icon">{{ icon(t.type) }}</span>
        <span class="toast-msg">{{ t.message }}</span>
      </div>
    </transition-group>
  </div>
</template>

<script setup>
import { toasts } from '@/utils/toast'

function icon(type) {
  if (type === 'success') return '✅'
  if (type === 'error') return '❌'
  return 'ℹ️'
}

function dismiss(id) {
  const i = toasts.findIndex((t) => t.id === id)
  if (i >= 0) toasts.splice(i, 1)
}
</script>

<style scoped>
.toast-host {
  position: fixed;
  top: 70px;
  right: 16px;
  z-index: 500;
  display: flex;
  flex-direction: column;
  gap: 8px;
  pointer-events: none;
  max-width: min(360px, calc(100vw - 32px));
}
.toast {
  pointer-events: auto;
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 0.82rem;
  line-height: 1.5;
  color: #e2e8f0;
  background: rgba(30, 41, 59, 0.92);
  border: 1px solid rgba(255, 255, 255, 0.12);
  backdrop-filter: blur(8px);
  box-shadow: 0 10px 26px rgba(2, 6, 23, 0.35);
  cursor: pointer;
  word-break: break-word;
}
html:not(.dark) .toast {
  color: #1e293b;
  background: rgba(255, 255, 255, 0.95);
  border-color: rgba(15, 23, 42, 0.1);
}
.toast.success {
  border-color: rgba(74, 222, 128, 0.4);
}
.toast.error {
  border-color: rgba(248, 113, 113, 0.4);
}
.toast-icon {
  flex-shrink: 0;
}
.toast-msg {
  min-width: 0;
}

.toast-enter-active,
.toast-leave-active {
  transition: all 0.25s ease;
}
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(24px);
}
</style>
