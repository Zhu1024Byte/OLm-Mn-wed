<template>
  <div class="api-page fade-in">
    <!-- API 服务状态 -->
    <section class="glass-card card">
      <h3 class="card-title">{{ t('api.service') }}</h3>

      <div class="setting-row">
        <div class="info">
          <div class="label">{{ t('api.enable') }}</div>
          <div class="desc">{{ t('api.enableDesc') }}</div>
        </div>
        <label class="switch-big">
          <input type="checkbox" :checked="settings.api_enabled" @change="toggleApi" />
          <span class="switch-track"></span>
        </label>
      </div>

      <div class="setting-row">
        <div class="info">
          <div class="label">{{ t('api.endpoint') }}</div>
          <div class="desc">{{ t('api.endpointDesc') }}</div>
        </div>
        <div class="endpoint">
          <code class="endpoint-url">{{ apiBaseUrl }}</code>
          <button class="copy-btn" :title="t('api.copy')" @click="copyEndpoint">📋</button>
        </div>
      </div>

      <div class="setting-row">
        <div class="info">
          <div class="label">{{ t('api.port') }}</div>
          <div class="desc">{{ t('api.portDesc') }}</div>
        </div>
        <div class="port-row">
          <input v-model.number="portInput" class="glass-input port-input" type="number" min="1024" max="65535" />
          <button class="btn-small" :disabled="savingPort" @click="savePort">
            {{ savingPort ? t('common.loading') : t('common.save') }}
          </button>
        </div>
      </div>
    </section>

    <!-- API Keys -->
    <section class="glass-card card">
      <h3 class="card-title">{{ t('api.keys') }}</h3>

      <div class="key-create">
        <input
          v-model="newKeyName"
          class="glass-input"
          :placeholder="t('api.keyNamePlaceholder')"
          @keydown.enter="createKey"
        />
        <button class="btn-primary" :disabled="!newKeyName.trim() || busy" @click="createKey">
          <IconPlus class="w-4 h-4" /> {{ t('api.createKey') }}
        </button>
      </div>

      <p v-if="justCreated" class="new-key">
        {{ t('api.newKeyHint') }}<br />
        <code class="key-value">{{ justCreated }}</code>
        <button class="copy-btn" @click="copyText(justCreated)">📋 {{ t('api.copy') }}</button>
      </p>

      <div v-if="!keys.length" class="empty-hint">{{ t('api.noKeys') }}</div>
      <div v-else class="key-list">
        <div v-for="k in keys" :key="k.id" class="key-row">
          <div class="key-info">
            <div class="key-name">
              <template v-if="editingId === k.id">
                <input
                  v-model="editingName"
                  class="glass-input key-edit"
                  @keydown.enter="commitRename(k)"
                  @keydown.esc="editingId = null"
                  @blur="commitRename(k)"
                />
              </template>
              <template v-else>
                <span @dblclick="startRename(k)">{{ k.name }}</span>
                <span v-if="!k.enabled" class="tag-off">{{ t('api.disabled') }}</span>
              </template>
            </div>
            <div class="key-meta">
              <code class="key-mask">{{ k.key }}</code>
              <span class="key-last">{{ t('api.lastUsed') }}: {{ k.last_used ? fmtDate(k.last_used) : t('api.never') }}</span>
            </div>
          </div>
          <div class="key-actions">
            <button class="btn-small" :title="t('api.copy')" @click="copyText(k.key)">📋</button>
            <button class="btn-small danger" :disabled="busy" @click="deleteTarget = k.id">
              {{ t('common.delete') }}
            </button>
          </div>
        </div>
      </div>
    </section>

    <!-- 使用示例 -->
    <section class="glass-card card">
      <h3 class="card-title">{{ t('api.examples') }}</h3>
      <pre class="code-example"><code>{{ curlExample }}</code></pre>
    </section>

    <!-- 删除确认 -->
    <ConfirmDialog
      v-if="deleteTarget"
      :title="t('api.deleteTitle')"
      :message="t('api.deleteKeyConfirm')"
      :confirm-text="t('common.delete')"
      @confirm="doDeleteKey"
      @cancel="deleteTarget = null"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '@/api'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import { IconPlus } from '@/components/icons'

const { t } = useI18n()

const settings = ref({ api_enabled: true, api_port: 3001, web_port: 3000 })
const portInput = ref(3001)
const savingPort = ref(false)
const keys = ref([])
const newKeyName = ref('')
const justCreated = ref('')
const busy = ref(false)
const editingId = ref(null)
const editingName = ref('')
const error = ref('')
const deleteTarget = ref(null)

const apiBaseUrl = computed(() => {
  const host = window.location.hostname || 'localhost'
  return `http://${host}:${settings.value.api_port}`
})

const curlExample = computed(() => `curl http://localhost:${settings.value.api_port}/v1/chat/completions \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer sk-olmwed-..." \\
  -d '{
    "model": "qwen3:8b",
    "messages": [{"role": "user", "content": "你好"}],
    "stream": false
  }'`)

onMounted(async () => {
  await Promise.all([loadSettings(), loadKeys()])
})

async function loadSettings() {
  try {
    const { data } = await api.get('/settings')
    settings.value = data
    portInput.value = data.api_port
  } catch (e) {
    error.value = e.response?.data?.detail || t('common.error')
  }
}

async function toggleApi(e) {
  const enabled = e.target.checked
  try {
    const { data } = await api.patch('/settings', { api_enabled: enabled })
    settings.value.api_enabled = data.api_enabled
  } catch (err) {
    error.value = err.response?.data?.detail || t('common.error')
    e.target.checked = !enabled
  }
}

async function savePort() {
  savingPort.value = true
  try {
    const { data } = await api.patch('/settings', { api_port: portInput.value })
    settings.value.api_port = data.api_port
    alert(t('api.portSaved'))
  } catch (e) {
    error.value = e.response?.data?.detail || t('common.error')
  } finally {
    savingPort.value = false
  }
}

async function loadKeys() {
  try {
    const { data } = await api.get('/keys')
    keys.value = data
  } catch (e) {
    error.value = e.response?.data?.detail || t('common.error')
  }
}

async function createKey() {
  busy.value = true
  error.value = ''
  try {
    const { data } = await api.post('/keys', { name: newKeyName.value.trim() })
    newKeyName.value = ''
    justCreated.value = data.key
    await loadKeys()
  } catch (e) {
    error.value = e.response?.data?.detail || t('common.error')
  } finally {
    busy.value = false
  }
}

function startRename(k) {
  editingId.value = k.id
  editingName.value = k.name
}

async function commitRename(k) {
  if (editingId.value !== k.id) return
  const name = editingName.value.trim()
  editingId.value = null
  if (!name || name === k.name) return
  try {
    await api.patch(`/keys/${k.id}`, { name })
    await loadKeys()
  } catch (e) {
    /* ignore */
  }
}

async function doDeleteKey() {
  const id = deleteTarget.value
  deleteTarget.value = null
  busy.value = true
  try {
    await api.delete(`/keys/${id}`)
    await loadKeys()
  } catch (e) {
    error.value = e.response?.data?.detail || t('common.error')
  } finally {
    busy.value = false
  }
}

async function copyEndpoint() {
  await copyText(apiBaseUrl.value + '/v1/chat/completions')
}

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text)
  } catch {
    /* clipboard may be unavailable in insecure contexts */
  }
}

function fmtDate(v) {
  return new Date(v).toLocaleString()
}
</script>

<style scoped>
.api-page {
  max-width: 860px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.card {
  padding: 22px 24px;
}
.card-title {
  margin: 0 0 8px;
  font-size: 0.95rem;
  font-weight: 600;
  color: #e2e8f0;
}
html:not(.dark) .card-title {
  color: #1e293b;
}

.setting-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.07);
}
html:not(.dark) .setting-row {
  border-bottom-color: rgba(15, 23, 42, 0.07);
}
.setting-row:last-child {
  border-bottom: none;
}
.label {
  font-size: 0.9rem;
  font-weight: 500;
  color: #cbd5e1;
}
html:not(.dark) .label {
  color: #334155;
}
.desc {
  margin-top: 3px;
  font-size: 0.78rem;
  color: #94a3b8;
}

/* big switch */
.switch-big input {
  display: none;
}
.switch-track {
  display: block;
  width: 48px;
  height: 26px;
  border-radius: 14px;
  background: rgba(148, 163, 184, 0.4);
  position: relative;
  cursor: pointer;
  transition: background 0.2s ease;
}
.switch-track::after {
  content: '';
  position: absolute;
  top: 3px;
  left: 3px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #fff;
  transition: transform 0.2s ease;
}
.switch-big input:checked + .switch-track {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
}
.switch-big input:checked + .switch-track::after {
  transform: translateX(22px);
}

.endpoint {
  display: flex;
  align-items: center;
  gap: 8px;
}
.endpoint-url {
  padding: 8px 12px;
  border-radius: 9px;
  font-size: 0.82rem;
  color: #a5b4fc;
  background: rgba(99, 102, 241, 0.1);
  border: 1px solid rgba(129, 140, 248, 0.25);
}
.copy-btn {
  padding: 6px 10px;
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 8px;
  font-size: 0.78rem;
  color: #cbd5e1;
  background: transparent;
  cursor: pointer;
}
html:not(.dark) .copy-btn {
  border-color: rgba(15, 23, 42, 0.15);
  color: #475569;
}

.port-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.port-input {
  width: 110px;
}
.btn-small {
  padding: 6px 12px;
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
.btn-small.danger {
  color: #fca5a5;
  border-color: rgba(248, 113, 113, 0.4);
}
.btn-small:disabled {
  opacity: 0.5;
}
.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 9px 16px;
  border: none;
  border-radius: 11px;
  font-size: 0.85rem;
  font-weight: 600;
  color: #fff;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  cursor: pointer;
}
.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.key-create {
  display: flex;
  gap: 10px;
  margin: 12px 0;
}
.new-key {
  margin: 0 0 14px;
  padding: 12px 14px;
  border-radius: 10px;
  font-size: 0.82rem;
  line-height: 1.8;
  color: #a5b4fc;
  background: rgba(99, 102, 241, 0.1);
  border: 1px solid rgba(129, 140, 248, 0.3);
  word-break: break-all;
}
.key-value {
  font-size: 0.85rem;
  color: #c7d2fe;
}

.empty-hint {
  padding: 16px;
  font-size: 0.85rem;
  color: #64748b;
  border: 1px dashed rgba(148, 163, 184, 0.3);
  border-radius: 12px;
}

.key-list {
  display: flex;
  flex-direction: column;
}
.key-row {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}
html:not(.dark) .key-row {
  border-bottom-color: rgba(15, 23, 42, 0.06);
}
.key-row:last-child {
  border-bottom: none;
}
.key-info {
  flex: 1;
  min-width: 0;
}
.key-name {
  font-size: 0.9rem;
  font-weight: 600;
  color: #e2e8f0;
  display: flex;
  align-items: center;
  gap: 8px;
}
html:not(.dark) .key-name {
  color: #1e293b;
}
.key-edit {
  padding: 4px 8px;
  font-size: 0.85rem;
}
.tag-off {
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 0.68rem;
  color: #f87171;
  background: rgba(248, 113, 113, 0.12);
}
.key-meta {
  margin-top: 3px;
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.key-mask {
  font-size: 0.75rem;
  color: #94a3b8;
}
.key-last {
  font-size: 0.72rem;
  color: #64748b;
}
.key-actions {
  display: flex;
  gap: 6px;
}

.code-example {
  margin: 12px 0 0;
  padding: 14px 16px;
  border-radius: 12px;
  overflow-x: auto;
  font-size: 0.8rem;
  line-height: 1.7;
  color: #cbd5e1;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(148, 163, 184, 0.15);
}
html:not(.dark) .code-example {
  color: #334155;
  background: rgba(15, 23, 42, 0.05);
}

@media (max-width: 640px) {
  .setting-row {
    flex-direction: column;
    align-items: flex-start;
  }
  .key-create {
    flex-direction: column;
  }
}
</style>
