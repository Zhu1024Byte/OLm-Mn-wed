<template>
  <div class="placeholder fade-in">
    <div class="ph-icon glass">{{ emoji }}</div>
    <h2>{{ title }}</h2>
    <p class="muted">{{ t('common.comingSoon') }}</p>
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n'

defineProps({
  title: { type: String, required: true },
  emoji: { type: String, default: '🚧' },
})

const { t } = useI18n()
</script>

<style scoped>
.placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  text-align: center;
}
.ph-icon {
  width: 84px;
  height: 84px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 24px;
  font-size: 2.2rem;
}
.placeholder h2 {
  margin: 1.25rem 0 0.5rem;
  font-size: 1.35rem;
  color: #e2e8f0;
  transition: color 0.2s ease;
}
html:not(.dark) .placeholder h2 {
  color: #1e293b;
}
.muted {
  font-size: 0.9rem;
  color: #94a3b8;
}
</style>
