<template>
  <div class="models-page fade-in">
    <!-- 页头操作 -->
    <div class="page-header">
      <div class="header-left">
        <button class="btn-primary" :disabled="busy" @click="openUploadModal()">
          <IconPlus class="w-4 h-4" /> {{ t('models.uploadModel') }}
        </button>
        <button class="btn-ghost" :disabled="busy" @click="refreshAll">
          <IconRefresh class="w-4 h-4" /> {{ t('common.refresh') }}
        </button>
      </div>
      <div v-if="error" class="error-banner">⚠️ {{ error }}</div>
    </div>

    <!-- 已安装模型 + 本地文件（flex 两栏，占满屏幕宽度） -->
    <div class="main-grid">
      <section class="section models-col">
        <h3 class="section-title">{{ t('models.installed') }}（{{ models.length }}）</h3>
        <div v-if="!models.length && !loading" class="empty-hint">{{ t('models.noInstalled') }}</div>
        <div class="model-grid">
          <div v-for="m in models" :key="m.name" class="model-card glass-card">
            <div class="model-head">
              <div class="model-icon">🧠</div>
              <div class="model-info">
                <div class="model-name" :title="m.name">{{ m.name }}</div>
                <div class="model-meta">
                  <span class="meta-item">{{ fmtSize(m.size) }}</span>
                  <template v-if="m.details?.parameter_size">
                    <span class="meta-item">{{ m.details.parameter_size }}</span>
                    <span v-if="m.details.quantization_level" class="meta-item">{{ m.details.quantization_level }}</span>
                  </template>
                </div>
              </div>
              <span
                v-if="m.status"
                class="model-status"
                :class="{ ok: m.status === 'loaded' }"
                :title="t('chat.modelStatus')"
              >
                {{ m.status === 'loaded' ? '✅' : '⏳' }}
              </span>
            </div>
            <div v-if="loadingModel === m.name" class="load-bar">
              <div class="load-bar-fill"></div>
            </div>
            <div class="model-actions">
              <button
                v-if="m.status !== 'loaded'"
                class="btn-small primary"
                :disabled="!!loadingModel"
                @click="loadModel(m)"
              >
                {{ loadingModel === m.name ? t('models.loadingModel') : t('models.load') }}
              </button>
              <button
                v-if="m.status === 'loaded'"
                class="btn-small"
                :disabled="unloadingModel === m.name"
                @click="unloadModel(m)"
              >
                {{ unloadingModel === m.name ? t('models.unloading') : t('models.unload') }}
              </button>
              <button class="btn-small primary" @click="openConfig(m)">{{ t('common.edit') }}</button>
              <button class="btn-small danger" @click="openDelete(m)">{{ t('common.delete') }}</button>
            </div>
          </div>
        </div>
      </section>

      <section class="section local-col">
        <h3 class="section-title">{{ t('models.localFiles') }}（{{ localFiles.length }}）</h3>
        <div v-if="!localFiles.length && !loading" class="empty-hint">{{ t('models.noLocal') }}</div>
        <div v-if="localFiles.length" class="local-list glass-card">
          <div v-for="f in localFiles" :key="f.filename" class="local-row">
            <span class="local-file">📄 {{ f.filename }}</span>
            <span class="local-size">{{ fmtSize(f.size) }}</span>
            <button class="btn-small primary" :disabled="busy" @click="openImportModal(f)">
              {{ t('models.import') }}
            </button>
          </div>
        </div>
      </section>
    </div>

    <!-- 操作提示（导入/删除的 note） -->
    <div v-if="note" class="note-banner">ℹ️ {{ note }}</div>

    <!-- ================= 上传 / 导入弹窗 ================= -->
    <div v-if="uploadOpen" class="modal-mask" @click.self="closeUploadModal">
      <div class="modal glass-card">
        <h3 class="modal-title">
          {{ uploadMode === 'upload' ? t('models.uploadModel') : t('models.import') }}
        </h3>

        <div v-if="uploadMode === 'upload'" class="field">
          <button class="file-picker" @click="fileInput.click()">
            <span v-if="!uploadFile">📁 {{ t('models.chooseFile') }}</span>
            <span v-else>📄 {{ uploadFile.name }}</span>
          </button>
          <input
            ref="fileInput"
            type="file"
            accept=".gguf"
            class="hidden-input"
            @change="onFileChange"
          />
        </div>

        <div v-else class="field">
          <label class="field-label">{{ t('models.localFile') }}</label>
          <div class="local-file readonly">📄 {{ localTarget?.filename }}</div>
        </div>

        <div class="field">
          <label class="field-label">{{ t('models.modelName') }}</label>
          <input v-model="importName" class="glass-input" :placeholder="t('models.modelNamePlaceholder')" />
        </div>

        <p v-if="uploadError" class="error-text">{{ uploadError }}</p>

        <!-- 上传进度 -->
        <div v-if="busy" class="upload-progress">
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: uploadProgress + '%' }"></div>
          </div>
          <div class="progress-meta">
            <span class="progress-text">
              {{ uploadPhase === 'upload' ? t('models.uploadProgress', { p: uploadProgress }) : t('models.importing') }}
            </span>
            <button v-if="uploadPhase === 'upload'" class="btn-small danger" @click="cancelUpload">
              {{ t('models.uploadCancel') }}
            </button>
          </div>
        </div>

        <div class="modal-actions">
          <button class="btn-ghost" :disabled="busy" @click="closeUploadModal">{{ t('common.cancel') }}</button>
          <button class="btn-primary" :disabled="busy || !importName.trim()" @click="doImport">
            {{ busy ? t('common.loading') : t('models.import') }}
          </button>
        </div>
      </div>
    </div>

    <!-- ================= 配置弹窗 ================= -->
    <div v-if="configOpen" class="modal-mask" @click.self="configOpen = false">
      <div class="modal wide glass-card">
        <h3 class="modal-title">{{ t('models.configTitle') }} · {{ configModel?.name }}</h3>

        <div class="config-grid">
          <div class="field">
            <label class="field-label">num_ctx（上下文长度）</label>
            <input v-model.number="configForm.num_ctx" class="glass-input" type="number" min="256" max="131072" step="256" />
          </div>
          <div class="field">
            <label class="field-label">num_gpu（-1=全部GPU，0=纯CPU）</label>
            <input v-model.number="configForm.num_gpu" class="glass-input" type="number" min="-1" />
          </div>
          <div class="field">
            <label class="field-label">num_thread（CPU线程数，0=自动）</label>
            <input v-model.number="configForm.num_thread" class="glass-input" type="number" min="0" />
          </div>
          <div class="field">
            <label class="field-label">temperature（0–2）</label>
            <input v-model.number="configForm.temperature" class="glass-input" type="number" min="0" max="2" step="0.1" />
          </div>
        </div>

        <div class="field">
          <label class="field-label">{{ t('chat.systemPrompt') }}</label>
          <textarea v-model="configForm.system_prompt" class="glass-input" rows="3"></textarea>
        </div>

        <!-- 内存预估 -->
        <div class="estimate">
          <div class="estimate-head">
            <span>{{ t('models.estimate') }}</span>
            <button class="btn-small" :disabled="estimating" @click="doEstimate">
              {{ estimating ? t('common.loading') : t('models.estimateBtn') }}
            </button>
          </div>
          <div v-if="estimate" class="estimate-body">
            <div class="est-row">
              <span>{{ t('models.weights') }}</span><span>{{ estimate.weights_gb }} GB</span>
            </div>
            <div class="est-row">
              <span>KV cache（ctx={{ estimate.num_ctx }}）</span><span>{{ estimate.kv_cache_gb }} GB</span>
            </div>
            <div class="est-row total">
              <span>{{ t('models.total') }}</span><span>{{ estimate.total_gb }} GB</span>
            </div>
            <ul class="advice">
              <li v-for="(a, i) in estimate.advice" :key="i">{{ a }}</li>
            </ul>
          </div>
          <div v-else class="estimate-hint">{{ t('models.estimateHint') }}</div>
        </div>

        <div class="modal-actions">
          <button class="btn-ghost" @click="configOpen = false">{{ t('common.cancel') }}</button>
          <button class="btn-primary" :disabled="saving" @click="saveConfig">
            {{ saving ? t('common.loading') : t('common.save') }}
          </button>
        </div>
      </div>
    </div>

    <!-- ================= 删除确认 ================= -->
    <div v-if="deleteTarget" class="modal-mask" @click.self="deleteTarget = null">
      <div class="modal glass-card">
        <h3 class="modal-title">{{ t('models.deleteTitle') }}</h3>
        <p class="delete-text">{{ t('models.deleteConfirm') }} <code>{{ deleteTarget?.name }}</code></p>
        <label class="check-row">
          <input v-model="deleteFile" type="checkbox" />
          <span>{{ t('models.deleteFileToo') }}</span>
        </label>
        <div class="modal-actions">
          <button class="btn-ghost" @click="deleteTarget = null">{{ t('common.cancel') }}</button>
          <button class="btn-danger" :disabled="busy" @click="doDelete">
            {{ busy ? t('common.loading') : t('common.delete') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '@/api'
import { IconPlus, IconRefresh } from '@/components/icons'
import { toast } from '@/utils/toast'

const { t } = useI18n()

const models = ref([])
const localFiles = ref([])
const loading = ref(false)
const busy = ref(false)
const saving = ref(false)
const estimating = ref(false)
const error = ref('')

// upload / import modal
const uploadOpen = ref(false)
const uploadMode = ref('upload') // 'upload' | 'local'
const uploadFile = ref(null)
const fileInput = ref(null)
const localTarget = ref(null)
const importName = ref('')
const uploadError = ref('')
const uploadProgress = ref(0)
const uploadPhase = ref('') // 'upload' | 'import'
let uploadCtrl = null

// config modal
const configOpen = ref(false)
const configModel = ref(null)
const configForm = ref({ num_ctx: 4096, num_gpu: -1, num_thread: 0, temperature: 0.7, system_prompt: '' })
const estimate = ref(null)

// load model
const loadingModel = ref(null)
const unloadingModel = ref(null)
const note = ref('')

// delete modal
const deleteTarget = ref(null)
const deleteFile = ref(false)

onMounted(refreshAll)

async function refreshAll() {
  await Promise.all([loadModels(), loadLocalFiles()])
}

async function loadModels() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await api.get('/ollama/tags')
    models.value = data.models || []
  } catch (e) {
    error.value = e.response?.data?.detail || t('common.error')
  } finally {
    loading.value = false
  }
}

async function loadLocalFiles() {
  try {
    const { data } = await api.get('/models/local')
    localFiles.value = data.files || []
  } catch (e) {
    /* non-fatal */
  }
}

// ---- load model ----
async function loadModel(m) {
  loadingModel.value = m.name
  note.value = ''
  try {
    await api.post(`/models/${encodeURIComponent(m.name)}/load`)
    // 轮询状态直到 loaded（或超时）
    await pollModelStatus(m.name, 90)
  } catch (e) {
    error.value = e.response?.data?.detail || e.message || t('models.loadFailed')
  } finally {
    loadingModel.value = null
    await loadModels()
  }
}

async function pollModelStatus(name, maxSeconds) {
  const start = Date.now()
  while (Date.now() - start < maxSeconds * 1000) {
    await new Promise((r) => setTimeout(r, 2000))
    try {
      const { data } = await api.get('/ollama/tags')
      const m = (data.models || []).find((x) => x.name === name)
      const st = m?.status
      if (st === 'loaded') return true
      if (st && st !== 'unloaded' && st !== 'loading') return false
    } catch (e) {
      /* keep polling */
    }
  }
  return false
}

// ---- unload model ----
async function unloadModel(m) {
  unloadingModel.value = m.name
  note.value = ''
  try {
    const { data } = await api.post(`/models/${encodeURIComponent(m.name)}/unload`)
    if (data.note) {
      note.value = data.note
      setTimeout(() => (note.value = ''), 6000)
    }
    toast(t('models.unloaded'), 'success')
    // 轮询状态直到 unloaded
    const start = Date.now()
    while (Date.now() - start < 30000) {
      await new Promise((r) => setTimeout(r, 2000))
      const { data: tags } = await api.get('/ollama/tags')
      const mm = (tags.models || []).find((x) => x.name === m.name)
      if (mm?.status !== 'loaded') break
    }
  } catch (e) {
    toast(e.response?.data?.detail || e.message || t('common.error'), 'error')
  } finally {
    unloadingModel.value = null
    await loadModels()
  }
}

function fmtSize(bytes) {
  if (!bytes) return '-'
  const gb = bytes / 1024 ** 3
  if (gb >= 1) return `${gb.toFixed(2)} GB`
  const mb = bytes / 1024 ** 2
  if (mb >= 1) return `${mb.toFixed(1)} MB`
  return `${bytes} B`
}

// ---- upload / import ----
function openUploadModal() {
  uploadMode.value = 'upload'
  uploadFile.value = null
  importName.value = ''
  uploadError.value = ''
  uploadOpen.value = true
}

function openImportModal(file) {
  uploadMode.value = 'local'
  localTarget.value = file
  importName.value = file.filename.replace(/\.gguf$/i, '')
  uploadError.value = ''
  uploadOpen.value = true
}

function closeUploadModal() {
  if (busy.value) return
  uploadOpen.value = false
}

function onFileChange(e) {
  const file = e.target.files?.[0]
  if (file) {
    uploadFile.value = file
    importName.value = safeBaseName(file.name)
  }
  e.target.value = ''
}

// 文件名安全化：保留 Unicode 字母/数字/中文，仅替换空白与危险符号
function safeBaseName(name) {
  const base = (name || 'model').replace(/\.gguf$/i, '')
  const safe = base.replace(/[^\p{L}\p{N}._\-]+/gu, '_').replace(/^_+|_+$/g, '')
  return safe || 'model'
}

/**
 * XMLHttpRequest 单块上传（raw bytes）。
 * 绕开 axios 对 File 的 multipart/transform 处理与拦截器干扰。
 */
function uploadRaw(file, url, { signal } = {}) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('PUT', url)
    xhr.setRequestHeader('Content-Type', 'application/octet-stream')
    xhr.setRequestHeader('Authorization', `Bearer ${localStorage.getItem('olmwed_token') || ''}`)
    xhr.onload = () => {
      let data = {}
      try {
        data = JSON.parse(xhr.responseText)
      } catch {
        /* non-JSON error body */
      }
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(data)
      } else {
        const err = new Error(data.detail || `HTTP ${xhr.status}`)
        err.status = xhr.status
        reject(err)
      }
    }
    xhr.onerror = () => reject(new Error('网络错误，上传失败'))
    xhr.onabort = () => {
      const err = new Error('canceled')
      err.code = 'ERR_CANCELED'
      reject(err)
    }
    if (signal) {
      const onAbort = () => xhr.abort()
      if (signal.aborted) onAbort()
      else signal.addEventListener('abort', onAbort, { once: true })
    }
    xhr.send(file)
  })
}

// 分块大小（与后端 UPLOAD_CHUNK_SIZE 一致）
const UPLOAD_CHUNK = 64 * 1024 * 1024

/**
 * 分块上传：文件切成 64MiB 块串行上传，单块失败自动重试。
 * 块粒度更新进度（不会产生数万次进度回调导致浏览器卡死），
 * 后端按偏移量幂等写入，重试/断点安全。
 */
async function uploadChunked(file, safeName, { signal, onProgress }) {
  const total = Math.max(1, Math.ceil(file.size / UPLOAD_CHUNK))
  const base = `/api/models/upload/chunk?filename=${encodeURIComponent(safeName)}`

  for (let i = 0; i < total; i++) {
    const start = i * UPLOAD_CHUNK
    const blob = file.slice(start, start + UPLOAD_CHUNK)

    let lastErr = null
    for (let attempt = 1; attempt <= 3; attempt++) {
      try {
        await uploadRaw(blob, `${base}&index=${i}`, { signal })
        lastErr = null
        break
      } catch (e) {
        lastErr = e
        if (e.code === 'ERR_CANCELED' || attempt === 3) throw e
        await new Promise((r) => setTimeout(r, 1000 * attempt)) // 退避重试
      }
    }
    if (lastErr) throw lastErr

    onProgress(Math.round(((i + 1) / total) * 100))
  }

  // 全部块上传完成 -> 校验文件大小
  const { data } = await api.post(
    '/models/upload/finalize',
    { filename: safeName, size: file.size },
    { timeout: 30000 },
  )
  return data
}

async function doImport() {
  busy.value = true
  uploadError.value = ''
  uploadProgress.value = 0
  uploadPhase.value = ''
  try {
    let filename
    if (uploadMode.value === 'upload') {
      if (!uploadFile.value) {
        uploadError.value = t('models.chooseFile')
        return
      }
      uploadPhase.value = 'upload'
      uploadCtrl = new AbortController()
      const safeName = safeBaseName(uploadFile.value.name) + '.gguf'
      // 大文件上传可能耗时较长（数 GB 需要几分钟）
      toast(t('models.uploadingBig') + ' ' + uploadFile.value.name, 'info', 6000)
      const result = await uploadChunked(uploadFile.value, safeName, {
        signal: uploadCtrl.signal,
        onProgress: (p) => {
          uploadProgress.value = p
        },
      })
      filename = result.filename
      toast(t('models.uploadDone'), 'success')
    } else {
      filename = localTarget.value.filename
    }

    // 上传完成后立即保存记录（即使后续导入失败，文件已在服务器，可重试导入）
    uploadPhase.value = 'import'
    let importResult = null
    try {
      importResult = await api.post('/models/import', { filename, name: importName.value.trim() }, { timeout: 120000 })
    } catch (e) {
      // 导入失败（如 llama-swap 重启慢/超时）：文件已上传，提示可从本地文件列表重新导入
      toast(t('models.uploadDone'), 'success')
      toast(t('models.importRetryHint'), 'error', 8000)
      uploadOpen.value = false
      await refreshAll()
      return
    }
    const { data } = importResult
    if (data.note) {
      note.value = data.note
      setTimeout(() => (note.value = ''), 12000)
    }
    uploadOpen.value = false
    if (data.status === 'registered') {
      // llama-swap 重启需要几秒，延迟刷新让新模型出现在列表
      await new Promise((r) => setTimeout(r, 5000))
    }
    await refreshAll()
  } catch (e) {
    if (e.code === 'ERR_CANCELED' || e.message?.includes('canceled')) {
      uploadError.value = t('models.uploadCancelled')
    } else {
      uploadError.value = e.response?.data?.detail || e.message || t('common.error')
    }
    // 上传失败也刷新本地文件列表（可能残留半文件，方便用户清理/重试）
    loadLocalFiles()
  } finally {
    busy.value = false
    uploadPhase.value = ''
    uploadCtrl = null
  }
}

function cancelUpload() {
  uploadCtrl?.abort()
}

// ---- config ----
async function openConfig(model) {
  configModel.value = model
  configForm.value = {
    num_ctx: model.config?.num_ctx ?? 4096,
    num_gpu: model.config?.num_gpu ?? -1,
    num_thread: model.config?.num_thread ?? 0,
    temperature: model.config?.temperature ?? 0.7,
    system_prompt: model.config?.system_prompt ?? '',
  }
  estimate.value = null
  configOpen.value = true
}

async function saveConfig() {
  saving.value = true
  try {
    const { data } = await api.put(`/models/${encodeURIComponent(configModel.value.name)}/config`, configForm.value)
    if (data.sync_note) {
      note.value = data.sync_note
      setTimeout(() => (note.value = ''), 12000)
    }
    configOpen.value = false
    await loadModels()
  } catch (e) {
    error.value = e.response?.data?.detail || t('common.error')
  } finally {
    saving.value = false
  }
}

async function doEstimate() {
  estimating.value = true
  try {
    const { data } = await api.get(
      `/models/${encodeURIComponent(configModel.value.name)}/estimate`,
      { params: { num_ctx: configForm.value.num_ctx, num_gpu: configForm.value.num_gpu } },
    )
    estimate.value = data
  } catch (e) {
    error.value = e.response?.data?.detail || t('common.error')
  } finally {
    estimating.value = false
  }
}

// ---- delete ----
function openDelete(model) {
  deleteTarget.value = model
  deleteFile.value = false
}

async function doDelete() {
  busy.value = true
  try {
    const { data } = await api.delete('/models', {
      params: { name: deleteTarget.value.name, delete_file: deleteFile.value },
    })
    if (data.note) {
      note.value = data.note
      setTimeout(() => (note.value = ''), 12000)
    }
    deleteTarget.value = null
    // OpenAI 兼容后端删除需重启 llama-swap，延迟刷新让列表更新
    await new Promise((r) => setTimeout(r, 5000))
    await refreshAll()
  } catch (e) {
    error.value = e.response?.data?.detail || t('common.error')
  } finally {
    busy.value = false
  }
}
</script>

<style scoped>
.models-page {
  /* 占满内容区，避免两侧留白 */
  min-height: 100%;
}

/* 已安装模型（弹性主区）+ 本地文件（固定侧栏） */
.main-grid {
  display: flex;
  gap: 20px;
  align-items: flex-start;
}
.models-col {
  flex: 1;
  min-width: 0;
}
.local-col {
  width: 320px;
  flex-shrink: 0;
}
@media (max-width: 1100px) {
  .main-grid {
    flex-direction: column;
  }
  .local-col {
    width: 100%;
  }
}

.note-banner {
  margin: 6px 0 0;
  padding: 10px 14px;
  border-radius: 10px;
  font-size: 0.82rem;
  line-height: 1.6;
  color: #a5b4fc;
  background: rgba(99, 102, 241, 0.1);
  border: 1px solid rgba(129, 140, 248, 0.3);
  word-break: break-all;
}

.model-status {
  flex-shrink: 0;
  font-size: 0.95rem;
}
/* 加载进度条（不确定动画） */
.load-bar {
  height: 5px;
  border-radius: 4px;
  background: rgba(148, 163, 184, 0.2);
  overflow: hidden;
}
.load-bar-fill {
  height: 100%;
  width: 40%;
  border-radius: 4px;
  background: linear-gradient(90deg, #6366f1, #8b5cf6);
  animation: load-sweep 1.2s ease-in-out infinite;
}
@keyframes load-sweep {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(350%);
  }
}

.page-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 18px;
  flex-wrap: wrap;
}
.header-left {
  display: flex;
  gap: 10px;
}
.error-banner {
  padding: 8px 14px;
  border-radius: 10px;
  font-size: 0.82rem;
  color: #fca5a5;
  background: rgba(248, 113, 113, 0.1);
  border: 1px solid rgba(248, 113, 113, 0.3);
}

.section {
  margin-bottom: 26px;
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

.model-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}
.model-card {
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.model-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 28px rgba(2, 6, 23, 0.25);
}
.model-head {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}
.model-icon {
  flex-shrink: 0;
  width: 46px;
  height: 46px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 13px;
  font-size: 1.35rem;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.3), rgba(139, 92, 246, 0.25));
}
.model-info {
  flex: 1;
  min-width: 0;
}
.model-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.95rem;
  font-weight: 600;
  color: #e2e8f0;
}
html:not(.dark) .model-name {
  color: #1e293b;
}
.model-meta {
  margin-top: 4px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.meta-item {
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 0.72rem;
  color: #94a3b8;
  background: rgba(148, 163, 184, 0.12);
}
.model-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.local-list {
  padding: 4px 14px;
}
.local-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}
html:not(.dark) .local-row {
  border-bottom-color: rgba(15, 23, 42, 0.06);
}
.local-row:last-child {
  border-bottom: none;
}
.local-file {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.86rem;
  color: #cbd5e1;
}
html:not(.dark) .local-file {
  color: #334155;
}
.local-size {
  font-size: 0.78rem;
  color: #94a3b8;
}
.local-file.readonly {
  padding: 9px 12px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.04);
}

/* buttons */
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
  box-shadow: 0 6px 16px rgba(99, 102, 241, 0.35);
  cursor: pointer;
  transition: transform 0.15s ease;
}
.btn-primary:hover:not(:disabled) {
  transform: translateY(-1px);
}
.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.btn-ghost {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 9px 14px;
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 11px;
  font-size: 0.85rem;
  color: #cbd5e1;
  background: transparent;
  cursor: pointer;
}
html:not(.dark) .btn-ghost {
  color: #475569;
  border-color: rgba(15, 23, 42, 0.15);
}
.btn-ghost:disabled {
  opacity: 0.5;
  cursor: not-allowed;
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
.btn-small.primary {
  color: #a5b4fc;
  border-color: rgba(129, 140, 248, 0.4);
}
.btn-small.danger {
  color: #fca5a5;
  border-color: rgba(248, 113, 113, 0.4);
}
.btn-small:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.08);
}
.btn-danger {
  padding: 9px 16px;
  border: none;
  border-radius: 11px;
  font-size: 0.85rem;
  font-weight: 600;
  color: #fff;
  background: linear-gradient(135deg, #f43f5e, #e11d48);
  cursor: pointer;
}
.btn-danger:disabled {
  opacity: 0.5;
}

/* modal */
.modal-mask {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px 16px;
  overflow-y: auto;
  background: rgba(2, 6, 23, 0.55);
  backdrop-filter: blur(4px);
}
.modal {
  width: 100%;
  max-width: 460px;
  margin: auto;
  max-height: calc(100vh - 48px);
  overflow-y: auto;
  padding: 24px;
}
.modal.wide {
  max-width: 620px;
}
.modal-title {
  margin: 0 0 18px;
  font-size: 1.05rem;
  font-weight: 600;
  color: #e2e8f0;
}
html:not(.dark) .modal-title {
  color: #1e293b;
}
.field {
  margin-bottom: 14px;
}
.field-label {
  display: block;
  margin-bottom: 6px;
  font-size: 0.8rem;
  color: #94a3b8;
}
.error-text {
  margin: 4px 0 10px;
  font-size: 0.8rem;
  color: #f87171;
}
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 18px;
}

.file-picker {
  width: 100%;
  padding: 26px 14px;
  border: 1.5px dashed rgba(129, 140, 248, 0.5);
  border-radius: 12px;
  font-size: 0.88rem;
  color: #a5b4fc;
  background: rgba(99, 102, 241, 0.06);
  cursor: pointer;
  transition: background 0.15s ease;
}
.file-picker:hover {
  background: rgba(99, 102, 241, 0.12);
}
.hidden-input {
  display: none;
}

/* 上传进度 */
.upload-progress {
  margin: 6px 0 12px;
  padding: 12px 14px;
  border-radius: 11px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.1);
}
html:not(.dark) .upload-progress {
  background: rgba(15, 23, 42, 0.04);
  border-color: rgba(15, 23, 42, 0.1);
}
.progress-bar {
  height: 8px;
  border-radius: 6px;
  background: rgba(148, 163, 184, 0.25);
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  border-radius: 6px;
  background: linear-gradient(90deg, #6366f1, #8b5cf6);
  transition: width 0.15s ease;
}
.progress-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 8px;
}
.progress-text {
  font-size: 0.78rem;
  color: #94a3b8;
}

.config-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 14px;
}

/* estimate */
.estimate {
  margin-top: 6px;
  padding: 14px;
  border-radius: 12px;
  border: 1px solid rgba(129, 140, 248, 0.25);
  background: rgba(99, 102, 241, 0.06);
}
.estimate-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 0.85rem;
  font-weight: 600;
  color: #a5b4fc;
}
.estimate-body {
  font-size: 0.82rem;
}
.est-row {
  display: flex;
  justify-content: space-between;
  padding: 5px 0;
  color: #cbd5e1;
}
html:not(.dark) .est-row {
  color: #334155;
}
.est-row.total {
  border-top: 1px solid rgba(129, 140, 248, 0.3);
  margin-top: 4px;
  padding-top: 8px;
  font-weight: 700;
  color: #e2e8f0;
}
html:not(.dark) .est-row.total {
  color: #1e293b;
}
.advice {
  margin: 8px 0 0;
  padding-left: 1.2em;
  color: #94a3b8;
}
.advice li {
  margin: 3px 0;
  line-height: 1.5;
}
.estimate-hint {
  font-size: 0.78rem;
  color: #94a3b8;
}

.delete-text {
  margin: 0 0 12px;
  font-size: 0.9rem;
  color: #cbd5e1;
}
html:not(.dark) .delete-text {
  color: #334155;
}
.delete-text code {
  color: #fca5a5;
}
.check-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.85rem;
  color: #94a3b8;
  cursor: pointer;
}
</style>
