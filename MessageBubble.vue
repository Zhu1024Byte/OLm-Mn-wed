<template>
  <div class="bubble-row" :class="message.role">
    <div v-if="message.role === 'assistant'" class="avatar assistant">🤖</div>

    <div class="bubble-wrap">
      <div class="bubble" :class="[message.role, { error: message.error }]">
        <Markdown
          v-if="message.role === 'assistant' && !message.error"
          :content="displayContent"
        />
        <span v-else-if="message.error" class="err-text">⚠️ {{ message.error }}</span>
        <span v-else class="user-text">{{ message.content }}</span>
        <span v-if="isStreaming" class="cursor"></span>
      </div>

      <!-- 操作按钮（悬停显示） -->
      <div v-if="showActions" class="msg-actions">
        <button
          v-if="message.role === 'assistant' && !message.pending && !message.error"
          class="msg-action"
          :title="t('chat.regenerate')"
          @click="$emit('regenerate')"
        >
          🔄
        </button>
        <button
          v-if="!message.pending && !message.error"
          class="msg-action"
          :title="copied ? t('chat.copied') : t('chat.copy')"
          @click="copy"
        >
          {{ copied ? '✅' : '📋' }}
        </button>
      </div>
    </div>

    <div v-if="message.role === 'user'" class="avatar user">👤</div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Markdown from './Markdown.vue'

const props = defineProps({
  message: { type: Object, required: true },
  streamingText: { type: String, default: '' },
  isStreaming: { type: Boolean, default: false },
  showRegenerate: { type: Boolean, default: false },
})

defineEmits(['regenerate'])

const { t } = useI18n()

// While a reply is streaming, show the live partial text.
const displayContent = computed(() =>
  props.message.pending ? props.streamingText : props.message.content,
)

// 操作按钮：用户消息总是显示；assistant 仅最后一条（父组件控制）显示
const showActions = computed(() => {
  if (props.isStreaming || props.message.pending) return false
  return props.message.role === 'user' || props.showRegenerate
})

const copied = ref(false)
async function copy() {
  try {
    await navigator.clipboard.writeText(props.message.content || '')
    copied.value = true
    setTimeout(() => (copied.value = false), 1500)
  } catch {
    /* clipboard unavailable */
  }
}
</script>

<style scoped>
.bubble-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 18px;
}
.bubble-row.user {
  flex-direction: row-reverse;
}

.avatar {
  flex-shrink: 0;
  width: 34px;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 11px;
  font-size: 1.05rem;
}
.avatar.assistant {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.35), rgba(139, 92, 246, 0.3));
  border: 1px solid rgba(99, 102, 241, 0.3);
}
.avatar.user {
  background: linear-gradient(135deg, rgba(34, 211, 238, 0.3), rgba(59, 130, 246, 0.3));
  border: 1px solid rgba(34, 211, 238, 0.3);
}

.bubble-wrap {
  max-width: min(78%, 760px);
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.bubble-row.user .bubble-wrap {
  align-items: flex-end;
}

.bubble {
  padding: 12px 16px;
  border-radius: 16px;
  font-size: 0.92rem;
}
.bubble.assistant {
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.06);
  backdrop-filter: blur(10px);
  border-top-left-radius: 4px;
  color: #e2e8f0;
}
.bubble.user {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff;
  border-top-right-radius: 4px;
  box-shadow: 0 6px 16px rgba(99, 102, 241, 0.3);
}
.bubble.error {
  border: 1px solid rgba(248, 113, 113, 0.4);
  background: rgba(248, 113, 113, 0.1);
}
.err-text {
  font-size: 0.85rem;
  color: #fca5a5;
}

.user-text {
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.7;
}

/* 操作按钮 */
.msg-actions {
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.15s ease;
}
.bubble-wrap:hover .msg-actions {
  opacity: 1;
}
.msg-action {
  padding: 3px 8px;
  border: none;
  border-radius: 7px;
  font-size: 0.78rem;
  color: #94a3b8;
  background: transparent;
  cursor: pointer;
}
.msg-action:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #e2e8f0;
}
html:not(.dark) .msg-action:hover {
  background: rgba(15, 23, 42, 0.08);
  color: #1e293b;
}

/* blinking cursor while streaming */
.cursor {
  display: inline-block;
  width: 8px;
  height: 1.1em;
  margin-left: 2px;
  vertical-align: text-bottom;
  border-radius: 2px;
  background: #a5b4fc;
  animation: blink 1s step-end infinite;
}
@keyframes blink {
  50% {
    opacity: 0;
  }
}
</style>
