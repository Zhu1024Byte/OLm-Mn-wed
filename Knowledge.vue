<template>
  <div class="knowledge-page fade-in">
    <!-- 上传区 -->
    <div
      class="dropzone"
      :class="{ dragging }"
      @dragover.prevent="dragging = true"
      @dragleave.prevent="dragging = false"
      @drop.prevent="onDrop"
      @click="fileInput.click()"
    >
      <div class="dz-icon">📚</div>
      <p class="dz-title">{{ t('knowledge.dropTitle') }}</p>
      <p class="dz-sub">{{ t('knowledge.dropSub') }}</p>
      <input
        ref="fileInput"
        type="file"
        accept=".txt,.md,.pdf"
        multiple
        class="hidden-input"
        @change="onFileChange"
      />
    </div>

    <p v-if="uploading" class="uploading">
      <span class="spinner"></span> {{ t('knowledge.indexing') }}
    </p>
    <p v-if="error" class="error-banner">⚠️ {{ error }}</p>

    <!-- 文档列表 -->
    <section class="section">
      <h3 class="section-title">{{ t('knowledge.documents') }}（{{ documents.length }}）</h3>
      <div v-if="!documents.length && !uploading" class="empty-hint">{{ t('knowledge.empty') }}</div>
      <div v-if="documents.length" class="doc-list glass-card">
        <div v-for="d in documents" :key="d.id" class="doc-row">
          <span class="doc-icon">📄</span>
          <div class="doc-info">
            <div class="doc-name" :title="d.name">{{ d.name }}</div>
            <div class="doc-meta">
              {{ t('knowledge.chunks', { n: d.chunk_count }) }} · {{ fmtDate(d.created_at) }}
            </div>
          </div>
          <button class="btn-small danger" :disabled="busy" @click="deleteTarget = d.id">
            {{ t('common.delete') }}
          </button>
        </div>
      </div>
    </section>

    <p class="embed-hint">
      💡 {{ t('knowledge.embedHint') }} <code>ollama pull nomic-embed-text</code>
    </p>

    <!-- 删除确认 -->
    <ConfirmDialog
      v-if="deleteTarget"
      :title="t('knowledge.deleteTitle')"
      :message="t('knowledge.deleteConfirm')"
      @confirm="doDelete"
      @cancel="deleteTarget = null"
    />
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '@/api'
import ConfirmDialog from '@/components/ConfirmDialog.vue'

const { t } = useI18n()

const documents = ref([])
const uploading = ref(false)
const busy = ref(false)
const dragging = ref(false)
const error = ref('')
const fileInput = ref(null)
const deleteTarget = ref(null)

onMounted(loadDocuments)

async function loadDocuments() {
  try {
    const { data } = await api.get('/knowledge/documents')
    documents.value = data
  } catch (e) {
    error.value = e.response?.data?.detail || t('common.error')
  }
}

function onDrop(e) {
  dragging.value = false
  handleFiles(e.dataTransfer?.files)
}

function onFileChange(e) {
  handleFiles(e.target.files)
  e.target.value = ''
}

async function handleFiles(files) {
  if (!files?.length || uploading.value) return
  error.value = ''
  uploading.value = true
  try {
    for (const file of files) {
      const fd = new FormData()
      fd.append('file', file)
      await api.post('/knowledge/upload', fd)
    }
    await loadDocuments()
  } catch (e) {
    error.value = e.response?.data?.detail || e.message || t('common.error')
  } finally {
    uploading.value = false
  }
}

async function doDelete() {
  const id = deleteTarget.value
  deleteTarget.value = null
  busy.value = true
  try {
    await api.delete(`/knowledge/documents/${id}`)
    await loadDocuments()
  } catch (e) {
    error.value = e.response?.data?.detail || t('common.error')
  } finally {
    busy.value = false
  }
}

function fmtDate(v) {
  if (!v) return ''
  const d = new Date(v)
  return d.toLocaleString()
}
</script>

<style scoped>
.knowledge-page {
  max-width: 900px;
  margin: 0 auto;
}

.dropzone {
  padding: 42px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  border: 1.5px dashed rgba(129, 140, 248, 0.5);
  border-radius: 18px;
  background: rgba(99, 102, 241, 0.05);
  cursor: pointer;
  transition: all 0.15s ease;
}
.dropzone:hover,
.dropzone.dragging {
  background: rgba(99, 102, 241, 0.12);
  border-color: rgba(129, 140, 248, 0.85);
}
.dz-icon {
  font-size: 2.2rem;
}
.dz-title {
  margin: 10px 0 4px;
  font-size: 0.98rem;
  font-weight: 600;
  color: #e2e8f0;
}
html:not(.dark) .dz-title {
  color: #1e293b;
}
.dz-sub {
  margin: 0;
  font-size: 0.8rem;
  color: #94a3b8;
}
.hidden-input {
  display: none;
}

.uploading {
  margin: 14px 0 0;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.85rem;
  color: #a5b4fc;
}
.spinner {
  width: 15px;
  height: 15px;
  border: 2px solid rgba(129, 140, 248, 0.3);
  border-top-color: #818cf8;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
.error-banner {
  margin: 14px 0 0;
  padding: 10px 14px;
  border-radius: 10px;
  font-size: 0.82rem;
  color: #fca5a5;
  background: rgba(248, 113, 113, 0.1);
  border: 1px solid rgba(248, 113, 113, 0.3);
}

.section {
  margin-top: 26px;
}
.section-title {
  margin: 0 0 12px;
  font-size: 0.95rem;
  font-weight: 600;
  color: #e2e8f0;
}
html:not(.dark) .section-title {
  color: #1e293b;
}
.empty-hint {
  padding: 18px;
  font-size: 0.85rem;
  color: #64748b;
  border: 1px dashed rgba(148, 163, 184, 0.3);
  border-radius: 12px;
}

.doc-list {
  padding: 4px 16px;
}
.doc-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}
html:not(.dark) .doc-row {
  border-bottom-color: rgba(15, 23, 42, 0.06);
}
.doc-row:last-child {
  border-bottom: none;
}
.doc-icon {
  font-size: 1.1rem;
}
.doc-info {
  flex: 1;
  min-width: 0;
}
.doc-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.88rem;
  color: #e2e8f0;
}
html:not(.dark) .doc-name {
  color: #1e293b;
}
.doc-meta {
  margin-top: 2px;
  font-size: 0.75rem;
  color: #94a3b8;
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
  cursor: not-allowed;
}

.embed-hint {
  margin-top: 20px;
  font-size: 0.78rem;
  color: #64748b;
}
.embed-hint code {
  color: #a5b4fc;
}
</style>
