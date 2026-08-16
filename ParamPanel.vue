<template>
  <aside class="side-panel glass" :class="{ collapsed: !panelOpen }">
    <div class="panel-header">
      <span v-if="panelOpen" class="panel-title">{{ t('chat.panel') }}</span>
      <button
        class="panel-toggle"
        :title="panelOpen ? t('chat.panel') + ' »' : t('chat.panel') + ' «'"
        @click="$emit('toggle-panel')"
      >
        <span v-if="panelOpen">»</span>
        <span v-else class="panel-gear">⚙</span>
      </button>
    </div>

    <div v-if="panelOpen" class="panel-body">
      <!-- 模型：状态 + 加载 -->
      <label class="panel-label">{{ t('chat.model') }}</label>
      <div class="panel-model">
        <span class="model-status-chip" :class="{ ok: currentModel?.status === 'loaded' }">
          {{ currentModel?.status === 'loaded' ? '✅' : '⏳' }}
          {{ modelName || t('chat.selectModel') }}
        </span>
        <button
          v-if="modelName && currentModel?.status !== 'loaded'"
          class="btn-small primary"
          :disabled="!!loadingModel"
          @click="$emit('load-model')"
        >
          {{ loadingModel ? t('chat.loadingModel') : t('models.load') }}
        </button>
        <button
          v-if="modelName && currentModel?.status === 'loaded'"
          class="btn-small"
          :disabled="!!unloadingModel"
          @click="$emit('unload-model')"
        >
          {{ unloadingModel ? t('models.unloading') : t('models.unload') }}
        </button>
      </div>

      <!-- 人格 -->
      <label class="panel-label">{{ t('chat.persona') }}</label>
      <div class="persona-row">
        <select
          :value="personaId"
          class="glass-input persona-select"
          :title="t('chat.persona')"
          @change="$emit('persona-change', $event.target.value)"
        >
          <option value="">{{ t('chat.personaNone') }}</option>
          <option v-for="p in personas" :key="p.id" :value="p.id">{{ p.name }}</option>
        </select>
        <button class="btn-small" :title="t('chat.personaManage')" @click="$emit('persona-manage')">🛠</button>
        <button
          class="btn-small"
          :title="t('chat.personaSaveHint')"
          :disabled="!systemPrompt.trim()"
          @click="$emit('persona-save')"
        >
          💾
        </button>
      </div>

      <label class="panel-label">{{ t('chat.systemPrompt') }}</label>
      <textarea
        :value="systemPrompt"
        class="panel-textarea"
        :placeholder="t('chat.systemPromptPlaceholder')"
        rows="6"
        @input="$emit('update:systemPrompt', $event.target.value)"
      ></textarea>

      <!-- 上下文长度 -->
      <label class="panel-label">num_ctx（{{ t('chat.numCtx') }}）</label>
      <div class="panel-slider">
        <input :value="numCtx" type="range" min="512" max="16384" step="512" @input="$emit('update:numCtx', Number($event.target.value))" />
        <span class="panel-val">{{ numCtx }}</span>
      </div>
      <p class="panel-hint">💡 {{ t('chat.ctxHint') }}</p>

      <!-- 模型运行参数 -->
      <div class="panel-grid">
        <div class="panel-field">
          <label class="panel-label">num_gpu</label>
          <input
            :value="numGpu"
            class="panel-num-input"
            type="number"
            min="-1"
            @input="$emit('update:numGpu', Number($event.target.value))"
          />
        </div>
        <div class="panel-field">
          <label class="panel-label">num_thread</label>
          <input
            :value="numThread"
            class="panel-num-input"
            type="number"
            min="0"
            @input="$emit('update:numThread', Number($event.target.value))"
          />
        </div>
      </div>

      <label class="panel-label">{{ t('chat.temperature') }}</label>
      <div class="panel-slider">
        <input
          :value="temperature"
          type="range"
          min="0"
          max="2"
          step="0.1"
          @input="$emit('update:temperature', Number($event.target.value))"
        />
        <span class="panel-val">{{ Number(temperature).toFixed(1) }}</span>
      </div>

      <button class="btn-small save-default" :disabled="!modelName" @click="$emit('save-default')">
        💾 {{ t('chat.saveDefault') }}
      </button>
    </div>
  </aside>
</template>

<script setup>
import { useI18n } from 'vue-i18n'

defineProps({
  panelOpen: Boolean,
  modelName: { type: String, default: '' },
  currentModel: { type: Object, default: null },
  loadingModel: Boolean,
  unloadingModel: Boolean,
  personas: { type: Array, default: () => [] },
  personaId: { type: String, default: '' },
  systemPrompt: { type: String, default: '' },
  temperature: { type: Number, default: 0.7 },
  numCtx: { type: Number, default: 4096 },
  numGpu: { type: Number, default: -1 },
  numThread: { type: Number, default: 0 },
})

defineEmits([
  'toggle-panel',
  'load-model',
  'unload-model',
  'persona-change',
  'persona-manage',
  'persona-save',
  'update:systemPrompt',
  'update:temperature',
  'update:numCtx',
  'update:numGpu',
  'update:numThread',
  'save-default',
])

const { t } = useI18n()
</script>

<style scoped>
/* ---------------- 右侧面板 ---------------- */
.side-panel {
  flex-shrink: 0;
  width: 280px;
  display: flex;
  flex-direction: column;
  border-radius: 16px;
  overflow: hidden;
  transition: width 0.2s ease;
  position: relative;
  z-index: 30;
}
.side-panel.collapsed {
  width: 44px;
}
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 10px 12px 14px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}
html:not(.dark) .panel-header {
  border-bottom-color: rgba(15, 23, 42, 0.08);
}
.panel-title {
  font-size: 0.85rem;
  font-weight: 600;
  color: #cbd5e1;
  white-space: nowrap;
}
html:not(.dark) .panel-title {
  color: #334155;
}
.panel-toggle {
  width: 30px;
  height: 30px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  color: #94a3b8;
  background: transparent;
  cursor: pointer;
  flex-shrink: 0;
}
.panel-toggle:hover {
  background: rgba(255, 255, 255, 0.12);
  color: #e2e8f0;
}
html:not(.dark) .panel-toggle:hover {
  background: rgba(15, 23, 42, 0.08);
  color: #1e293b;
}
.side-panel.collapsed .panel-header {
  justify-content: center;
  padding: 10px 4px;
  border-bottom: none;
  flex: 1;
}
.side-panel.collapsed .panel-toggle {
  width: 100%;
  height: 100%;
  border-radius: 0;
  font-size: 1.2rem;
}
.panel-gear {
  font-size: 1.05rem;
}
.side-panel.collapsed .panel-body {
  display: none;
}

.panel-body {
  flex: 1;
  overflow-y: auto;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.panel-label {
  font-size: 0.78rem;
  font-weight: 500;
  color: #94a3b8;
}
.panel-textarea {
  width: 100%;
  resize: vertical;
  padding: 10px 12px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 11px;
  font-size: 0.82rem;
  line-height: 1.6;
  color: #e2e8f0;
  background: rgba(255, 255, 255, 0.05);
  outline: none;
  font-family: inherit;
}
html:not(.dark) .panel-textarea {
  color: #1e293b;
  border-color: rgba(15, 23, 42, 0.15);
  background: rgba(255, 255, 255, 0.7);
}
.panel-textarea:focus {
  border-color: rgba(129, 140, 248, 0.6);
}
.panel-slider {
  display: flex;
  align-items: center;
  gap: 10px;
}
.panel-slider input[type='range'] {
  flex: 1;
  accent-color: #6366f1;
}
.panel-val {
  min-width: 34px;
  text-align: right;
  font-size: 0.82rem;
  color: #cbd5e1;
}
html:not(.dark) .panel-val {
  color: #334155;
}

/* 模型状态 + 加载 */
.panel-model {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 2px;
}
.model-status-chip {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding: 6px 10px;
  border-radius: 9px;
  font-size: 0.8rem;
  color: #fbbf24;
  background: rgba(251, 191, 36, 0.1);
  border: 1px solid rgba(251, 191, 36, 0.3);
}
.model-status-chip.ok {
  color: #4ade80;
  background: rgba(74, 222, 128, 0.1);
  border-color: rgba(74, 222, 128, 0.3);
}

/* 参数输入 */
.panel-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
.panel-num-input {
  width: 100%;
  padding: 6px 10px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 9px;
  font-size: 0.82rem;
  color: #e2e8f0;
  background: rgba(255, 255, 255, 0.05);
  outline: none;
}
html:not(.dark) .panel-num-input {
  color: #1e293b;
  border-color: rgba(15, 23, 42, 0.15);
  background: rgba(255, 255, 255, 0.7);
}
.save-default {
  width: 100%;
}
.panel-hint {
  margin: -4px 0 0;
  font-size: 0.72rem;
  color: #64748b;
  line-height: 1.5;
}

/* 人格 */
.persona-row {
  display: flex;
  align-items: center;
  gap: 6px;
}
.persona-select {
  flex: 1;
  min-width: 0;
  padding: 7px 10px;
  font-size: 0.8rem;
}
.btn-small {
  flex-shrink: 0;
  padding: 6px 10px;
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 8px;
  font-size: 0.78rem;
  color: #cbd5e1;
  background: transparent;
  cursor: pointer;
}
html:not(.dark) .btn-small {
  color: #475569;
  border-color: rgba(15, 23, 42, 0.15);
}
.btn-small.primary {
  color: #a5b4fc;
  border-color: rgba(129, 140, 248, 0.4);
}
.btn-small:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@media (max-width: 900px) {
  .side-panel {
    position: fixed;
    right: 12px;
    top: 84px;
    bottom: 12px;
    z-index: 30;
    box-shadow: 0 16px 40px rgba(2, 6, 23, 0.4);
  }
}
</style>
