<template>
  <div class="cd-mask">
    <div class="cd-dialog glass-card">
      <h3 class="cd-title">{{ title }}</h3>
      <p class="cd-text">{{ message }}</p>
      <div class="cd-actions">
        <button class="cd-btn ghost" @click="cancel">{{ t('common.cancel') }}</button>
        <button class="cd-btn danger" @click="confirm">{{ confirmText || t('common.confirm') }}</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'

defineProps({
  title: { type: String, default: '' },
  message: { type: String, default: '' },
  confirmText: { type: String, default: '' },
})

const emit = defineEmits(['confirm', 'cancel'])
const { t } = useI18n()

// 全屏锁定：弹窗打开期间背景不可滚动、不可点击（只能选择删除或取消）
onMounted(() => {
  document.body.style.overflow = 'hidden'
})
onBeforeUnmount(() => {
  document.body.style.overflow = ''
})

function confirm() {
  emit('confirm')
}
function cancel() {
  emit('cancel')
}
</script>

<style scoped>
.cd-mask {
  position: fixed;
  inset: 0;
  z-index: 200;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  background: rgba(2, 6, 23, 0.6);
  backdrop-filter: blur(4px);
  /* 拦截一切背景交互 */
  pointer-events: auto;
}
.cd-dialog {
  width: 100%;
  max-width: 400px;
  padding: 24px;
}
.cd-title {
  margin: 0 0 10px;
  font-size: 1.02rem;
  font-weight: 600;
  color: #e2e8f0;
}
html:not(.dark) .cd-title {
  color: #1e293b;
}
.cd-text {
  margin: 0;
  font-size: 0.9rem;
  line-height: 1.7;
  color: #cbd5e1;
}
html:not(.dark) .cd-text {
  color: #334155;
}
.cd-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}
.cd-btn {
  padding: 9px 18px;
  border: none;
  border-radius: 11px;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
}
.cd-btn.ghost {
  color: #cbd5e1;
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.18);
}
html:not(.dark) .cd-btn.ghost {
  color: #475569;
  border-color: rgba(15, 23, 42, 0.18);
}
.cd-btn.danger {
  color: #fff;
  background: linear-gradient(135deg, #f43f5e, #e11d48);
}
</style>
