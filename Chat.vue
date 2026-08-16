<template>
  <div class="chat-page">
    <!-- ===================== 会话列表 ===================== -->
    <aside class="conv-panel glass">
      <div class="conv-header">
        <button class="btn-new" :disabled="streaming" @click="newConversation">
          <IconPlus class="w-4 h-4" />
          <span>{{ t('chat.newConversation') }}</span>
        </button>
      </div>

      <div class="conv-list">
        <div v-if="!conversations.length" class="conv-empty">{{ t('chat.emptyConversations') }}</div>

        <div
          v-for="conv in conversations"
          :key="conv.id"
          class="conv-item"
          :class="{ active: conv.id === currentConvId }"
          @click="selectConversation(conv.id)"
        >
          <input
            v-if="editingId === conv.id"
            v-model="editingTitle"
            class="conv-edit"
            @click.stop
            @keydown.enter="commitRename(conv)"
            @keydown.esc="editingId = null"
            @blur="commitRename(conv)"
          />
          <template v-else>
            <span class="conv-title" @dblclick="startRename(conv)">{{ conv.title }}</span>
            <button
              class="conv-del"
              :title="t('chat.deleteConversation') + '（Ctrl+点击 直接删除）'"
              @click.stop="askDeleteConversation(conv.id, $event)"
            >
              ×
            </button>
          </template>
        </div>
      </div>
    </aside>

    <!-- ===================== 聊天主区域 ===================== -->
    <div class="chat-main glass">
      <div ref="msgBox" class="messages">
        <!-- 欢迎空态 -->
        <div v-if="!messages.length && !streaming" class="welcome">
          <div class="welcome-logo">◆</div>
          <h2>{{ t('chat.welcomeTitle') }}</h2>
          <p>{{ t('chat.welcomeDesc') }}</p>
          <div v-if="!models.length" class="warn">⚠️ {{ t('chat.noModels') }}</div>
        </div>

        <div v-if="loadError" class="load-error">⚠️ {{ loadError }}</div>

        <MessageBubble
          v-for="(msg, i) in messages"
          :key="msg.id"
          :message="msg"
          :streaming-text="msg.pending ? streamingText : ''"
          :is-streaming="streaming && msg.pending"
          :show-regenerate="
            !streaming &&
            msg.role === 'assistant' &&
            !msg.pending &&
            !msg.error &&
            i === messages.length - 1
          "
          @regenerate="regenerateMessage"
        />
      </div>

      <!-- 参数栏 + 输入框 -->
      <div class="composer">
        <div class="toolbar">
          <select
            v-model="modelName"
            class="tool-select"
            :title="t('chat.model')"
            @change="onModelChange"
          >
            <option value="" disabled>
              {{ models.length ? t('chat.selectModel') : t('chat.noModels') }}
            </option>
            <option v-for="m in models" :key="m.name" :value="m.name">{{ m.name }}</option>
          </select>

          <span
            v-if="currentModel"
            class="model-status"
            :class="{ loaded: currentModel.status === 'loaded' }"
            :title="t('chat.modelStatus')"
          >
            {{ currentModel.status === 'loaded' ? '✅' : '⏳' }}
            {{ currentModel.status === 'loaded' ? t('chat.loaded') : t('chat.unloaded') }}
          </span>

          <label class="tool-slider" :title="t('chat.temperature')">
            <span class="tool-label">🌡 {{ temperature.toFixed(1) }}</span>
            <input v-model.number="temperature" type="range" min="0" max="2" step="0.1" />
          </label>

          <label v-if="supportsThink" class="tool-toggle" :title="t('chat.thinkDesc')">
            <input v-model="think" type="checkbox" />
            <span class="switch"></span>
            <span class="tool-label">💭 {{ t('chat.think') }}</span>
          </label>

          <select
            v-if="supportsThink"
            v-model="effort"
            class="tool-select slim"
            :title="t('chat.effort')"
          >
            <option value="low">{{ t('chat.effortLow') }}</option>
            <option value="medium">{{ t('chat.effortMedium') }}</option>
            <option value="high">{{ t('chat.effortHigh') }}</option>
          </select>

          <select
            v-model="knowledgeId"
            class="tool-select slim"
            :title="t('chat.knowledge')"
          >
            <option value="">{{ t('chat.knowledgeNone') }}</option>
            <option v-for="d in knowledgeDocs" :key="d.id" :value="d.id">
              📚 {{ d.name }}
            </option>
          </select>

          <label class="tool-toggle disabled" :title="t('chat.mcp')">
            <input type="checkbox" disabled />
            <span class="switch"></span>
            <span class="tool-label">🔌 {{ t('chat.mcp') }}</span>
          </label>

          <button class="tool-btn disabled" disabled :title="t('chat.webSearch')">
            🌐 {{ t('chat.webSearch') }}
          </button>
        </div>

        <p v-if="noticeMsg" class="notice">ℹ️ {{ noticeMsg }}</p>

        <div class="input-row">
          <textarea
            v-model="input"
            class="chat-input"
            :placeholder="t('chat.inputPlaceholder')"
            rows="1"
            @keydown="onInputKeydown"
          ></textarea>
          <button
            v-if="!streaming"
            class="send-btn"
            :disabled="!input.trim() || !modelName"
            :title="t('chat.send')"
            @click="sendMessage"
          >
            <IconSend class="w-5 h-5" />
          </button>
          <button v-else class="send-btn stop" :title="t('chat.stop')" @click="stopStreaming">
            <span class="stop-icon"></span>
          </button>
        </div>
      </div>
    </div>

    <!-- ===================== 右侧参数面板 ===================== -->
    <ParamPanel
      :panel-open="panelOpen"
      :model-name="modelName"
      :current-model="currentModel"
      :loading-model="loadingModel"
      :unloading-model="unloadingModel"
      :personas="personas"
      :persona-id="personaId"
      :system-prompt="systemPrompt"
      :temperature="temperature"
      :num-ctx="numCtx"
      :num-gpu="numGpu"
      :num-thread="numThread"
      @toggle-panel="panelOpen = !panelOpen"
      @load-model="loadChatModel"
      @unload-model="unloadChatModel"
      @persona-change="onPersonaChange"
      @persona-manage="openPersonaModal"
      @persona-save="saveCurrentPersona"
      @update:system-prompt="systemPrompt = $event"
      @update:temperature="temperature = $event"
      @update:num-ctx="numCtx = $event"
      @update:num-gpu="numGpu = $event"
      @update:num-thread="numThread = $event"
      @save-default="saveDefaultConfig"
    />

    <!-- 人格管理弹窗 -->
    <div v-if="personaModal" class="modal-mask" @click.self="personaModal = false">
      <div class="modal wide glass-card">
        <h3 class="modal-title">{{ t('chat.personaManage') }}</h3>

        <div class="persona-layout">
          <!-- 列表 -->
          <div class="persona-list">
            <div
              v-for="p in personas"
              :key="p.id"
              class="persona-item"
              :class="{ active: personaForm.id === p.id }"
              @click="loadPersonaToForm(p)"
            >
              <span class="persona-item-name" :title="p.name">{{ p.name }}</span>
              <button class="persona-del" :title="t('common.delete')" @click.stop="askDeletePersona(p)">×</button>
            </div>
            <div v-if="!personas.length" class="persona-empty">{{ t('chat.personaEmpty') }}</div>
          </div>

          <!-- 编辑表单 -->
          <div class="persona-editor">
            <div class="field">
              <label class="field-label">{{ t('chat.personaName') }}</label>
              <input v-model="personaForm.name" class="glass-input" :placeholder="t('chat.personaName')" />
            </div>
            <div class="field">
              <label class="field-label">{{ t('chat.personaPrompt') }}</label>
              <textarea
                v-model="personaForm.prompt"
                class="glass-input persona-prompt-input"
                rows="6"
                :placeholder="t('chat.systemPromptPlaceholder')"
              ></textarea>
            </div>
            <div class="modal-actions">
              <button class="btn-ghost" @click="personaForm = { id: null, name: '', prompt: '' }">
                {{ t('chat.personaNew') }}
              </button>
              <button
                class="btn-primary"
                :disabled="!personaForm.name.trim()"
                @click="savePersonaForm"
              >
                {{ t('common.save') }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 删除会话确认 -->
    <ConfirmDialog
      v-if="deleteTarget"
      :title="t('chat.deleteConversation')"
      :message="t('chat.deleteConfirm')"
      @confirm="doDeleteConversation"
      @cancel="deleteTarget = null"
    />
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '@/api'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import MessageBubble from '@/components/MessageBubble.vue'
import ParamPanel from '@/components/chat/ParamPanel.vue'
import { IconPlus, IconSend } from '@/components/icons'
import { streamChat } from '@/utils/stream'
import { toast } from '@/utils/toast'

const { t } = useI18n()

// ---- state ----
const conversations = ref([])
const currentConvId = ref(null)
const currentConv = ref(null)
const models = ref([])
const modelName = ref('')
const temperature = ref(0.7)
const think = ref(true)
const effort = ref('medium')
const systemPrompt = ref('')
const numCtx = ref(4096)
const numGpu = ref(-1)
const numThread = ref(0)
const loadingModel = ref(false)
const unloadingModel = ref(false)
const input = ref('')
const streaming = ref(false)
const streamingText = ref('')
const abortCtrl = ref(null)
const panelOpen = ref(true)
const editingId = ref(null)
const editingTitle = ref('')
const loadError = ref('')
const noticeMsg = ref('')
const msgBox = ref(null)
// knowledge base (RAG)
const knowledgeDocs = ref([])
const knowledgeId = ref('')
// personas
const personas = ref([])
const personaId = ref('')
const personaModal = ref(false)
const personaForm = ref({ id: null, name: '', prompt: '' })
// confirm dialogs
const deleteTarget = ref(null)

// Reasoning-capable models get the thinking controls
const THINK_RE = /(qwen3|deepseek|r1|think|reason|qwq)/i
const supportsThink = computed(() => THINK_RE.test(modelName.value))
const messages = computed(() => currentConv.value?.messages || [])
const currentModel = computed(() => models.value.find((m) => m.name === modelName.value) || null)

// ---- lifecycle ----
onMounted(async () => {
  await Promise.all([loadModels(), loadConversations(), loadKnowledgeDocs(), loadPersonas()])
})

onBeforeUnmount(() => {
  abortCtrl.value?.abort()
})

// ---- data loading ----
async function loadModels() {
  try {
    const { data } = await api.get('/ollama/tags')
    models.value = data.models || []
  } catch (e) {
    loadError.value = e.response?.data?.detail || t('chat.ollamaDown')
  }
}

async function loadConversations() {
  try {
    const { data } = await api.get('/conversations')
    conversations.value = data
  } catch (e) {
    loadError.value = e.response?.data?.detail || t('common.error')
  }
}

async function loadKnowledgeDocs() {
  try {
    const { data } = await api.get('/knowledge/documents')
    knowledgeDocs.value = data || []
  } catch (e) {
    /* non-fatal */
  }
}

function onModelChange() {
  const m = models.value.find((x) => x.name === modelName.value)
  if (m?.config) {
    if (m.config.temperature != null) temperature.value = m.config.temperature
    if (m.config.system_prompt != null) systemPrompt.value = m.config.system_prompt
    if (m.config.num_ctx != null) numCtx.value = m.config.num_ctx
    if (m.config.num_gpu != null) numGpu.value = m.config.num_gpu
    if (m.config.num_thread != null) numThread.value = m.config.num_thread
  }
}

// ---- load model (chat panel) ----
async function loadChatModel() {
  if (!modelName.value || loadingModel.value) return
  loadingModel.value = true
  try {
    await api.post(`/models/${encodeURIComponent(modelName.value)}/load`)
    // 轮询状态直到 loaded
    const start = Date.now()
    while (Date.now() - start < 90000) {
      await new Promise((r) => setTimeout(r, 2000))
      const { data } = await api.get('/ollama/tags')
      const m = (data.models || []).find((x) => x.name === modelName.value)
      if (m?.status === 'loaded') break
    }
    toast(t('models.loadDone'), 'success')
  } catch (e) {
    toast(e.response?.data?.detail || e.message || t('models.loadFailed'), 'error')
  } finally {
    loadingModel.value = false
    loadModels()
  }
}

// ---- unload model (chat panel) ----
async function unloadChatModel() {
  if (!modelName.value || unloadingModel.value) return
  unloadingModel.value = true
  try {
    const { data } = await api.post(`/models/${encodeURIComponent(modelName.value)}/unload`)
    toast(data.note || t('models.unloaded'), 'success')
    // 轮询状态直到 unloaded
    const start = Date.now()
    while (Date.now() - start < 30000) {
      await new Promise((r) => setTimeout(r, 2000))
      const { data: tags } = await api.get('/ollama/tags')
      const m = (tags.models || []).find((x) => x.name === modelName.value)
      if (m?.status !== 'loaded') break
    }
  } catch (e) {
    toast(e.response?.data?.detail || e.message || t('models.unloaded'), 'error')
  } finally {
    unloadingModel.value = false
    loadModels()
  }
}

// ---- save model defaults ----
async function saveDefaultConfig() {
  if (!modelName.value) return
  try {
    const { data } = await api.put(`/models/${encodeURIComponent(modelName.value)}/config`, {
      num_ctx: numCtx.value,
      num_gpu: numGpu.value,
      num_thread: numThread.value,
      temperature: temperature.value,
      system_prompt: systemPrompt.value,
    })
    toast(data.sync_note || t('common.success'), 'success')
    loadModels()
  } catch (e) {
    toast(e.response?.data?.detail || t('common.error'), 'error')
  }
}

// ---- conversation management ----
async function selectConversation(id) {
  if (streaming.value) stopStreaming()
  try {
    const { data } = await api.get(`/conversations/${id}`)
    currentConvId.value = id
    currentConv.value = data
    streamingText.value = ''
    scrollToBottom()
  } catch (e) {
    loadError.value = e.response?.data?.detail || t('common.error')
  }
}

async function newConversation() {
  if (streaming.value) stopStreaming()
  const { data } = await api.post('/conversations', {})
  conversations.value.unshift(data)
  currentConvId.value = data.id
  currentConv.value = { ...data, messages: [] }
  input.value = ''
  streamingText.value = ''
}

function startRename(conv) {
  editingId.value = conv.id
  editingTitle.value = conv.title
}

async function commitRename(conv) {
  if (editingId.value !== conv.id) return
  const title = editingTitle.value.trim()
  editingId.value = null
  if (!title || title === conv.title) return
  try {
    const { data } = await api.patch(`/conversations/${conv.id}`, { title })
    conv.title = data.title
  } catch (e) {
    /* ignore */
  }
}

function askDeleteConversation(id, event) {
  // 按住 Ctrl 直接删除，跳过确认
  if (event?.ctrlKey || event?.metaKey) {
    deleteTarget.value = id
    doDeleteConversation()
    return
  }
  deleteTarget.value = id
}

async function doDeleteConversation() {
  const id = deleteTarget.value
  deleteTarget.value = null
  try {
    await api.delete(`/conversations/${id}`)
  } catch (e) {
    /* ignore */
  }
  conversations.value = conversations.value.filter((c) => c.id !== id)
  if (currentConvId.value === id) {
    currentConvId.value = null
    currentConv.value = null
  }
}

// ---- personas ----
async function loadPersonas() {
  try {
    const { data } = await api.get('/personas')
    personas.value = data || []
  } catch (e) {
    /* non-fatal */
  }
}

function applyPersona() {
  const p = personas.value.find((x) => x.id === Number(personaId.value))
  if (p) systemPrompt.value = p.prompt
}

// ParamPanel 选择人格（与 applyPersona 相同行为，供模板 @persona-change 使用）
function onPersonaChange(id) {
  personaId.value = id
  applyPersona()
}

async function saveCurrentPersona() {
  const prompt = systemPrompt.value.trim()
  if (!prompt) return
  try {
    if (personaId.value) {
      const p = personas.value.find((x) => x.id === Number(personaId.value))
      if (p) {
        await api.put(`/personas/${p.id}`, { name: p.name, prompt })
        p.prompt = prompt
      }
    } else {
      const { data } = await api.post('/personas', { name: '未命名人格', prompt })
      personas.value.unshift(data)
      personaId.value = data.id
    }
    toast(t('chat.personaSaved'), 'success')
  } catch (e) {
    toast(e.response?.data?.detail || t('common.error'), 'error')
  }
}

function openPersonaModal() {
  personaForm.value = { id: null, name: '', prompt: systemPrompt.value }
  personaModal.value = true
}

function loadPersonaToForm(p) {
  personaForm.value = { id: p.id, name: p.name, prompt: p.prompt }
}

async function savePersonaForm() {
  const { id, name, prompt } = personaForm.value
  try {
    if (id) {
      const { data } = await api.put(`/personas/${id}`, { name: name.trim(), prompt })
      const idx = personas.value.findIndex((x) => x.id === id)
      if (idx >= 0) personas.value[idx] = data
    } else {
      const { data } = await api.post('/personas', { name: name.trim(), prompt })
      personas.value.unshift(data)
    }
    personaModal.value = false
    toast(t('common.success'), 'success')
  } catch (e) {
    toast(e.response?.data?.detail || t('common.error'), 'error')
  }
}

function askDeletePersona(p) {
  if (window.confirm(t('chat.personaDeleteConfirm'))) {
    doDeletePersona(p.id)
  }
}

async function doDeletePersona(id) {
  try {
    await api.delete(`/personas/${id}`)
  } catch (e) {
    /* ignore */
  }
  personas.value = personas.value.filter((x) => x.id !== id)
  if (personaId.value === String(id)) {
    personaId.value = ''
  }
  if (personaForm.value.id === id) {
    personaForm.value = { id: null, name: '', prompt: '' }
  }
}

// ---- chat ----
function onInputKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

async function sendMessage() {
  const content = input.value.trim()
  if (!content || streaming.value) return
  if (!modelName.value) {
    loadError.value = t('chat.selectModel')
    return
  }
  loadError.value = ''

  // Ensure a conversation exists (create on first message)
  if (!currentConvId.value) {
    const { data } = await api.post('/conversations', {})
    conversations.value.unshift(data)
    currentConvId.value = data.id
    currentConv.value = { ...data, messages: [] }
  }

  const userMsg = { id: -Date.now(), role: 'user', content, model: modelName.value }
  const pendingMsg = { id: -Date.now() - 1, role: 'assistant', content: '', pending: true }
  currentConv.value.messages.push(userMsg, pendingMsg)
  input.value = ''
  streamingText.value = ''
  streaming.value = true
  abortCtrl.value = new AbortController()
  scrollToBottom()

  const finalize = (patch) => {
    const msgs = currentConv.value?.messages
    const idx = msgs?.findIndex((m) => m.id === pendingMsg.id)
    if (idx >= 0) Object.assign(msgs[idx], patch)
  }

  try {
    await streamChat(
      '/api/chat',
      {
        conversation_id: currentConvId.value,
        model: modelName.value,
        content,
        temperature: temperature.value,
        num_ctx: numCtx.value,
        num_gpu: numGpu.value,
        num_thread: numThread.value,
        think: supportsThink.value ? think.value : null,
        reasoning_effort: supportsThink.value ? effort.value : null,
        system_prompt: systemPrompt.value,
        knowledge_ids: knowledgeId.value ? [Number(knowledgeId.value)] : [],
      },
      {
        signal: abortCtrl.value.signal,
        onDelta: (piece) => {
          streamingText.value += piece
          scrollToBottom()
        },
        onNotice: (msg) => {
          toast(msg, 'info', 6000)
        },
        onDone: (evt) => {
          finalize({ content: evt.content, pending: false })
          streamingText.value = ''
        },
        onError: (err) => {
          finalize({ pending: false, error: err.message })
          streamingText.value = ''
        },
      },
    )
  } catch (e) {
    if (e.name !== 'AbortError' && currentConv.value) {
      finalize({ pending: false, error: e.message || t('common.error') })
    }
  } finally {
    streaming.value = false
    abortCtrl.value = null
    streamingText.value = ''
    loadConversations() // updated_at changed -> reorder the list
    scrollToBottom()
  }
}

function stopStreaming() {
  abortCtrl.value?.abort()
}

// ---- regenerate ----
async function regenerateMessage() {
  if (streaming.value || !currentConv.value || !currentConvId.value) return
  const msgs = currentConv.value.messages
  // 最后一条已完成的 assistant 消息
  let idx = -1
  for (let i = msgs.length - 1; i >= 0; i--) {
    if (msgs[i].role === 'assistant' && !msgs[i].pending && !msgs[i].error) {
      idx = i
      break
    }
  }
  if (idx < 0) return
  // 它前面的最后一条 user 消息（用于 RAG 检索 query）
  let query = ''
  for (let i = idx - 1; i >= 0; i--) {
    if (msgs[i].role === 'user') {
      query = msgs[i].content
      break
    }
  }
  // 转 pending 重新流式
  msgs[idx].pending = true
  msgs[idx].content = ''
  delete msgs[idx].error
  streamingText.value = ''
  streaming.value = true
  abortCtrl.value = new AbortController()
  scrollToBottom()

  const finalize = (patch) => {
    const m = currentConv.value?.messages[idx]
    if (m) Object.assign(m, patch)
  }

  try {
    await streamChat(
      '/api/chat',
      {
        conversation_id: currentConvId.value,
        model: modelName.value,
        content: query,
        regenerate: true,
        temperature: temperature.value,
        num_ctx: numCtx.value,
        num_gpu: numGpu.value,
        num_thread: numThread.value,
        think: supportsThink.value ? think.value : null,
        reasoning_effort: supportsThink.value ? effort.value : null,
        system_prompt: systemPrompt.value,
        knowledge_ids: knowledgeId.value ? [Number(knowledgeId.value)] : [],
      },
      {
        signal: abortCtrl.value.signal,
        onDelta: (piece) => {
          streamingText.value += piece
          scrollToBottom()
        },
        onDone: (evt) => {
          finalize({ content: evt.content, pending: false })
          streamingText.value = ''
        },
        onError: (err) => {
          finalize({ pending: false, error: err.message })
          streamingText.value = ''
        },
      },
    )
  } catch (e) {
    if (e.name !== 'AbortError') {
      finalize({ pending: false, error: e.message || t('common.error') })
    }
  } finally {
    streaming.value = false
    abortCtrl.value = null
    streamingText.value = ''
    loadConversations()
    scrollToBottom()
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (msgBox.value) msgBox.value.scrollTop = msgBox.value.scrollHeight
  })
}
</script>

<style scoped>
.chat-page {
  display: flex;
  gap: 14px;
  height: calc(100vh - 88px);
  min-height: 0;
}

/* ---------------- 会话面板 ---------------- */
.conv-panel {
  flex-shrink: 0;
  width: 230px;
  display: flex;
  flex-direction: column;
  border-radius: 16px;
  overflow: hidden;
}
.conv-header {
  padding: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}
html:not(.dark) .conv-header {
  border-bottom-color: rgba(15, 23, 42, 0.08);
}
.btn-new {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 9px 12px;
  border: none;
  border-radius: 11px;
  font-size: 0.88rem;
  font-weight: 600;
  color: #fff;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  box-shadow: 0 6px 16px rgba(99, 102, 241, 0.35);
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.btn-new:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 8px 20px rgba(99, 102, 241, 0.45);
}
.btn-new:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.conv-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.conv-empty {
  padding: 24px 10px;
  font-size: 0.78rem;
  color: #64748b;
  text-align: center;
}
.conv-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 9px 10px;
  border-radius: 10px;
  cursor: pointer;
  transition: background 0.12s ease;
}
.conv-item:hover {
  background: rgba(255, 255, 255, 0.06);
}
html:not(.dark) .conv-item:hover {
  background: rgba(15, 23, 42, 0.05);
}
.conv-item.active {
  background: rgba(99, 102, 241, 0.18);
  box-shadow: inset 2px 0 0 #818cf8;
}
.conv-title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.84rem;
  color: #cbd5e1;
  user-select: none;
}
html:not(.dark) .conv-title {
  color: #334155;
}
.conv-item.active .conv-title {
  color: #e2e8f0;
  font-weight: 500;
}
.conv-del {
  flex-shrink: 0;
  width: 22px;
  height: 22px;
  display: none;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 6px;
  font-size: 0.95rem;
  line-height: 1;
  color: #94a3b8;
  background: transparent;
  cursor: pointer;
}
.conv-item:hover .conv-del {
  display: inline-flex;
}
.conv-del:hover {
  color: #f87171;
  background: rgba(248, 113, 113, 0.15);
}
.conv-edit {
  flex: 1;
  min-width: 0;
  padding: 4px 6px;
  border: 1px solid rgba(129, 140, 248, 0.6);
  border-radius: 6px;
  font-size: 0.82rem;
  color: #e2e8f0;
  background: rgba(15, 23, 42, 0.5);
  outline: none;
}

/* ---------------- 聊天主区 ---------------- */
.chat-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  border-radius: 16px;
  overflow: hidden;
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 22px 24px;
}
.load-error {
  margin-bottom: 14px;
  padding: 10px 14px;
  border-radius: 10px;
  font-size: 0.82rem;
  color: #fca5a5;
  background: rgba(248, 113, 113, 0.1);
  border: 1px solid rgba(248, 113, 113, 0.3);
}

.welcome {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: #94a3b8;
}
.welcome-logo {
  width: 72px;
  height: 72px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 20px;
  font-size: 1.6rem;
  color: #fff;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  box-shadow: 0 14px 34px rgba(99, 102, 241, 0.4);
}
.welcome h2 {
  margin: 1.2rem 0 0.4rem;
  font-size: 1.3rem;
  color: #e2e8f0;
}
html:not(.dark) .welcome h2 {
  color: #1e293b;
}
.welcome p {
  max-width: 420px;
  font-size: 0.88rem;
  line-height: 1.7;
}
.warn {
  margin-top: 1rem;
  padding: 8px 14px;
  border-radius: 10px;
  font-size: 0.8rem;
  color: #fbbf24;
  background: rgba(251, 191, 36, 0.1);
}

/* ---------------- 输入区 ---------------- */
.composer {
  padding: 10px 14px 14px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}
html:not(.dark) .composer {
  border-top-color: rgba(15, 23, 42, 0.08);
}

.toolbar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}
.tool-select {
  height: 32px;
  max-width: 220px;
  padding: 0 8px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 9px;
  font-size: 0.78rem;
  color: #cbd5e1;
  background: rgba(255, 255, 255, 0.05);
  outline: none;
  cursor: pointer;
}
html:not(.dark) .tool-select {
  color: #334155;
  border-color: rgba(15, 23, 42, 0.15);
  background: rgba(255, 255, 255, 0.7);
}
.tool-select.slim {
  max-width: 90px;
}
.tool-select.disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

/* 模型状态徽章 */
.model-status {
  padding: 3px 10px;
  border-radius: 8px;
  font-size: 0.72rem;
  color: #fbbf24;
  background: rgba(251, 191, 36, 0.12);
  border: 1px solid rgba(251, 191, 36, 0.3);
  white-space: nowrap;
}
.model-status.loaded {
  color: #4ade80;
  background: rgba(74, 222, 128, 0.1);
  border-color: rgba(74, 222, 128, 0.3);
}

.tool-slider {
  display: flex;
  align-items: center;
  gap: 6px;
}
.tool-slider input[type='range'] {
  width: 90px;
  accent-color: #6366f1;
}
.tool-label {
  font-size: 0.76rem;
  color: #94a3b8;
  white-space: nowrap;
}

/* toggle switch */
.tool-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  user-select: none;
}
.tool-toggle.disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.tool-toggle input {
  display: none;
}
.switch {
  position: relative;
  width: 30px;
  height: 17px;
  border-radius: 10px;
  background: rgba(148, 163, 184, 0.35);
  transition: background 0.2s ease;
}
.switch::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 13px;
  height: 13px;
  border-radius: 50%;
  background: #fff;
  transition: transform 0.2s ease;
}
.tool-toggle input:checked + .switch {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
}
.tool-toggle input:checked + .switch::after {
  transform: translateX(13px);
}

.tool-btn {
  height: 32px;
  padding: 0 10px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 9px;
  font-size: 0.78rem;
  color: #cbd5e1;
  background: rgba(255, 255, 255, 0.05);
  cursor: pointer;
}
.tool-btn.disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.input-row {
  display: flex;
  align-items: flex-end;
  gap: 10px;
}
.notice {
  margin: 0 0 8px;
  padding: 7px 12px;
  border-radius: 9px;
  font-size: 0.78rem;
  color: #fbbf24;
  background: rgba(251, 191, 36, 0.1);
  border: 1px solid rgba(251, 191, 36, 0.25);
}
.chat-input {
  flex: 1;
  resize: none;
  min-height: 44px;
  max-height: 160px;
  padding: 11px 14px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 13px;
  font-size: 0.9rem;
  line-height: 1.5;
  color: #e2e8f0;
  background: rgba(255, 255, 255, 0.05);
  outline: none;
  transition: border-color 0.15s ease;
}
html:not(.dark) .chat-input {
  color: #1e293b;
  border-color: rgba(15, 23, 42, 0.15);
  background: rgba(255, 255, 255, 0.7);
}
.chat-input:focus {
  border-color: rgba(129, 140, 248, 0.6);
}
.chat-input::placeholder {
  color: #64748b;
}

.send-btn {
  flex-shrink: 0;
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 13px;
  color: #fff;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  box-shadow: 0 6px 16px rgba(99, 102, 241, 0.35);
  cursor: pointer;
  transition: transform 0.15s ease, opacity 0.15s ease;
}
.send-btn:hover:not(:disabled) {
  transform: translateY(-1px);
}
.send-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.send-btn.stop {
  background: linear-gradient(135deg, #f43f5e, #e11d48);
  box-shadow: 0 6px 16px rgba(244, 63, 94, 0.35);
}
.stop-icon {
  width: 14px;
  height: 14px;
  border-radius: 3px;
  background: #fff;
}

/* ---------------- 人格 ---------------- */
.persona-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
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
.btn-small:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ---------------- 弹窗（人格管理） ---------------- */
.modal-mask {
  position: fixed;
  inset: 0;
  z-index: 150;
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
  max-width: 680px;
}
.modal-title {
  margin: 0 0 16px;
  font-size: 1.05rem;
  font-weight: 600;
  color: #e2e8f0;
}
html:not(.dark) .modal-title {
  color: #1e293b;
}
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 16px;
}
.field {
  margin-bottom: 12px;
}
.field-label {
  display: block;
  margin-bottom: 6px;
  font-size: 0.8rem;
  color: #94a3b8;
}
.btn-ghost {
  padding: 9px 16px;
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 11px;
  font-size: 0.85rem;
  color: #cbd5e1;
  background: transparent;
  cursor: pointer;
}
html:not(.dark) .btn-ghost {
  color: #475569;
  border-color: rgba(15, 23, 42, 0.18);
}
.btn-primary {
  padding: 9px 18px;
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

.persona-layout {
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: 16px;
}
.persona-list {
  max-height: 300px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.persona-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  border-radius: 9px;
  cursor: pointer;
  transition: background 0.12s ease;
}
.persona-item:hover {
  background: rgba(255, 255, 255, 0.06);
}
html:not(.dark) .persona-item:hover {
  background: rgba(15, 23, 42, 0.05);
}
.persona-item.active {
  background: rgba(99, 102, 241, 0.18);
}
.persona-item-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.84rem;
  color: #cbd5e1;
}
html:not(.dark) .persona-item-name {
  color: #334155;
}
.persona-del {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  border: none;
  border-radius: 6px;
  font-size: 0.9rem;
  line-height: 1;
  color: #94a3b8;
  background: transparent;
  cursor: pointer;
}
.persona-del:hover {
  color: #f87171;
  background: rgba(248, 113, 113, 0.15);
}
.persona-empty {
  padding: 14px 8px;
  font-size: 0.8rem;
  color: #64748b;
  text-align: center;
}
.persona-editor {
  min-width: 0;
}
.persona-prompt-input {
  resize: vertical;
  font-family: inherit;
}
@media (max-width: 640px) {
  .conv-panel {
    display: none;
  }
  .persona-layout {
    grid-template-columns: 1fr;
  }
}
</style>
