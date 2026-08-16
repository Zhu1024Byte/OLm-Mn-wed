<template>
  <div class="settings-page fade-in">
    <!-- 外观 -->
    <section class="glass-card card">
      <h3 class="card-title">{{ t('settings.appearance') }}</h3>

      <div class="setting-row">
        <div class="info">
          <div class="label">{{ t('theme.title') }}</div>
          <div class="desc">{{ t('settings.themeDesc') }}</div>
        </div>
        <div class="segmented">
          <button
            v-for="opt in themeOptions"
            :key="opt.value"
            :class="{ active: settings.theme === opt.value }"
            @click="settings.setTheme(opt.value)"
          >
            {{ t(opt.labelKey) }}
          </button>
        </div>
      </div>

      <div class="setting-row">
        <div class="info">
          <div class="label">{{ t('language.title') }}</div>
        </div>
        <div class="segmented">
          <button
            :class="{ active: settings.locale === 'zh-CN' }"
            @click="settings.setLocale('zh-CN')"
          >
            {{ t('language.zh') }}
          </button>
          <button
            :class="{ active: settings.locale === 'en-US' }"
            @click="settings.setLocale('en-US')"
          >
            {{ t('language.en') }}
          </button>
        </div>
      </div>
    </section>

    <!-- 账号：修改用户名 -->
    <section class="glass-card card">
      <h3 class="card-title">{{ t('settings.account') }}</h3>

      <div class="setting-row">
        <div class="info">
          <div class="label">{{ t('settings.changeUsername') }}</div>
          <div class="desc">{{ t('settings.changeUsernameDesc', { name: auth.displayName }) }}</div>
        </div>
      </div>

      <form class="pw-form" @submit.prevent="changeUsername">
        <div class="field">
          <label class="field-label">{{ t('settings.newUsername') }}</label>
          <input
            v-model="uname"
            class="glass-input"
            type="text"
            minlength="2"
            maxlength="64"
            pattern="[a-zA-Z0-9_.\-]+"
            required
          />
        </div>
        <p v-if="unameMsg" class="form-msg" :class="{ ok: unameOk }">{{ unameMsg }}</p>
        <button class="btn-primary" type="submit" :disabled="unameSaving">
          {{ unameSaving ? t('common.loading') : t('common.save') }}
        </button>
      </form>
    </section>

    <!-- 安全：修改密码 -->
    <section class="glass-card card">
      <h3 class="card-title">{{ t('settings.security') }}</h3>

      <form class="pw-form" @submit.prevent="changePassword">
        <div class="field">
          <label class="field-label">{{ t('settings.oldPassword') }}</label>
          <input v-model="pw.old" class="glass-input" type="password" autocomplete="current-password" required />
        </div>
        <div class="field">
          <label class="field-label">{{ t('settings.newPassword') }}</label>
          <input v-model="pw.new1" class="glass-input" type="password" autocomplete="new-password" minlength="6" required />
        </div>
        <div class="field">
          <label class="field-label">{{ t('settings.confirmPassword') }}</label>
          <input v-model="pw.new2" class="glass-input" type="password" autocomplete="new-password" minlength="6" required />
        </div>

        <p v-if="pwMsg" class="form-msg" :class="{ ok: pwOk }">{{ pwMsg }}</p>

        <button class="btn-primary" type="submit" :disabled="pwSaving">
          {{ pwSaving ? t('common.loading') : t('common.save') }}
        </button>
      </form>
    </section>

    <!-- 模型后端 -->
    <section class="glass-card card">
      <h3 class="card-title">{{ t('settings.backend') }}</h3>

      <div v-if="backendInfo" class="backend-info">
        <div class="backend-row">
          <span class="bi-label">{{ t('settings.backendType') }}</span>
          <span class="bi-value">{{ backendInfo.backend_label }}</span>
        </div>
        <div class="backend-row">
          <span class="bi-label">{{ t('settings.backendUrl') }}</span>
          <span class="bi-value"><code>{{ backendInfo.backend_url }}</code></span>
        </div>
        <div class="backend-row">
          <span class="bi-label">{{ t('settings.backendEmbed') }}</span>
          <span class="bi-value">{{ backendInfo.embed_model }}</span>
        </div>
      </div>

      <div class="backend-actions">
        <button class="btn-ghost" :disabled="backendBusy" @click="askBackendAction('restart')">
          {{ t('settings.backendRestart') }}
        </button>
        <button class="btn-ghost" :disabled="backendBusy" @click="askBackendAction('stop')">
          {{ t('settings.backendStop') }}
        </button>
        <button class="btn-ghost" :disabled="backendBusy" @click="askBackendAction('start')">
          {{ t('settings.backendStart') }}
        </button>
      </div>
      <p v-if="backendMsg" class="form-msg" :class="{ ok: backendOk }">{{ backendMsg }}</p>
    </section>

    <!-- 系统：检查更新 -->
    <section class="glass-card card">
      <h3 class="card-title">{{ t('settings.system') }}</h3>

      <div class="setting-row">
        <div class="info">
          <div class="label">{{ t('settings.checkUpdate') }}</div>
          <div class="desc">{{ t('settings.checkUpdateDesc') }}</div>
        </div>
        <button class="btn-primary" :disabled="checking" @click="checkUpdate">
          {{ checking ? t('common.loading') : t('settings.checkNow') }}
        </button>
      </div>

      <div v-if="updateResult" class="update-result">
        <div class="up-row">
          <span class="up-name">Ollama</span>
          <template v-if="updateResult.ollama.current">
            <span class="up-ver">{{ t('settings.current') }}: {{ updateResult.ollama.current }}</span>
            <span v-if="updateResult.ollama.latest" class="up-ver">
              {{ t('settings.latest') }}: {{ updateResult.ollama.latest }}
            </span>
            <span v-if="updateResult.ollama.up_to_date === true" class="up-badge ok">✓</span>
            <span v-else-if="updateResult.ollama.up_to_date === false" class="up-badge warn">⚠️</span>
          </template>
          <span v-else class="up-note">{{ updateResult.ollama.note }}</span>
          <a
            v-if="updateResult.ollama.url"
            class="up-link"
            :href="updateResult.ollama.url"
            target="_blank"
            rel="noopener"
          >GitHub ↗</a>
        </div>

        <div class="up-row">
          <span class="up-name">OLm-Mn-wed</span>
          <span class="up-ver">{{ t('settings.current') }}: {{ updateResult.project.current }}</span>
          <template v-if="updateResult.project.latest">
            <span class="up-ver">{{ t('settings.latest') }}: {{ updateResult.project.latest }}</span>
            <span v-if="updateResult.project.up_to_date === true" class="up-badge ok">✓</span>
            <span v-else-if="updateResult.project.up_to_date === false" class="up-badge warn">⚠️</span>
          </template>
          <span v-if="updateResult.project.note" class="up-note">{{ updateResult.project.note }}</span>
          <a
            v-if="updateResult.project.url"
            class="up-link"
            :href="updateResult.project.url"
            target="_blank"
            rel="noopener"
          >GitHub ↗</a>
        </div>
      </div>
    </section>

    <!-- 后端操作确认 -->
    <ConfirmDialog
      v-if="backendConfirm"
      :title="t('settings.backendConfirmTitle')"
      :message="t('settings.backendConfirmMsg')"
      :confirm-text="t('common.confirm')"
      @confirm="doBackendAction"
      @cancel="backendConfirm = null"
    />
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '@/api'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import { useAuthStore } from '@/stores/auth'
import { useSettingsStore } from '@/stores/settings'

const { t } = useI18n()
const settings = useSettingsStore()
const auth = useAuthStore()

const themeOptions = [
  { value: 'dark', labelKey: 'theme.dark' },
  { value: 'light', labelKey: 'theme.light' },
  { value: 'system', labelKey: 'theme.system' },
]

// ---- change username ----
const uname = ref('')
const unameSaving = ref(false)
const unameMsg = ref('')
const unameOk = ref(false)

async function changeUsername() {
  unameMsg.value = ''
  unameOk.value = false
  const name = uname.value.trim()
  if (!/^[a-zA-Z0-9_.\-]{2,64}$/.test(name)) {
    unameMsg.value = t('settings.newUsername')
    return
  }
  unameSaving.value = true
  try {
    const { data } = await api.post('/auth/change-username', { new_username: name })
    auth.user = { ...auth.user, username: data.username }
    localStorage.setItem('olmwed_user', JSON.stringify(auth.user))
    uname.value = ''
    unameMsg.value = t('settings.usernameChanged')
    unameOk.value = true
  } catch (e) {
    unameMsg.value = e.response?.data?.detail || t('common.error')
  } finally {
    unameSaving.value = false
  }
}

// ---- change password ----
const pw = reactive({ old: '', new1: '', new2: '' })
const pwSaving = ref(false)
const pwMsg = ref('')
const pwOk = ref(false)

async function changePassword() {
  pwMsg.value = ''
  pwOk.value = false
  if (pw.new1 !== pw.new2) {
    pwMsg.value = t('settings.pwMismatch')
    return
  }
  if (pw.new1.length < 6) {
    pwMsg.value = t('settings.pwTooShort')
    return
  }
  pwSaving.value = true
  try {
    await api.post('/auth/change-password', { old_password: pw.old, new_password: pw.new1 })
    pwMsg.value = t('settings.pwChanged')
    pwOk.value = true
    pw.old = pw.new1 = pw.new2 = ''
  } catch (e) {
    pwMsg.value = e.response?.data?.detail || t('common.error')
  } finally {
    pwSaving.value = false
  }
}

// ---- update check ----
const checking = ref(false)
const updateResult = ref(null)

// ---- model backend ----
const backendInfo = ref(null)
const backendBusy = ref(false)
const backendMsg = ref('')
const backendOk = ref(false)
const backendConfirm = ref(null) // { action }

onMounted(async () => {
  try {
    const { data } = await api.get('/system/info')
    backendInfo.value = data
  } catch (e) {
    /* non-fatal */
  }
})

function askBackendAction(action) {
  backendConfirm.value = { action }
}

async function doBackendAction() {
  const { action } = backendConfirm.value
  backendConfirm.value = null
  backendBusy.value = true
  backendMsg.value = ''
  backendOk.value = false
  try {
    const { data } = await api.post('/system/backend/action', { action })
    backendMsg.value = `${action}: ${data.status}`
    backendOk.value = true
  } catch (e) {
    backendMsg.value = e.response?.data?.detail || t('common.error')
  } finally {
    backendBusy.value = false
  }
}

async function checkUpdate() {
  checking.value = true
  updateResult.value = null
  try {
    const { data } = await api.get('/update/check')
    updateResult.value = data
  } catch (e) {
    updateResult.value = {
      ollama: { note: e.response?.data?.detail || t('common.error') },
      project: { current: '0.1.0', note: '' },
    }
  } finally {
    checking.value = false
  }
}
</script>

<style scoped>
.settings-page {
  max-width: 760px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-bottom: 32px;
}

.card {
  padding: 22px 24px;
}
.card-title {
  margin: 0 0 6px;
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
  padding: 16px 0;
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

.segmented {
  display: flex;
  padding: 3px;
  gap: 2px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.05);
}
html:not(.dark) .segmented {
  border-color: rgba(15, 23, 42, 0.12);
  background: rgba(15, 23, 42, 0.04);
}
.segmented button {
  padding: 6px 14px;
  border: none;
  border-radius: 9px;
  font-size: 0.8rem;
  color: #94a3b8;
  background: transparent;
  cursor: pointer;
  transition: all 0.15s ease;
  white-space: nowrap;
}
.segmented button:hover {
  color: #e2e8f0;
}
html:not(.dark) .segmented button:hover {
  color: #1e293b;
}
.segmented button.active {
  color: #fff;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.35);
}

.pw-form {
  max-width: 400px;
  margin-top: 12px;
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
.form-msg {
  margin: 0 0 10px;
  font-size: 0.82rem;
  color: #f87171;
}
.form-msg.ok {
  color: #4ade80;
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
.btn-ghost:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 模型后端 */
.backend-info {
  margin: 10px 0 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.backend-row {
  display: flex;
  gap: 12px;
  font-size: 0.85rem;
}
.bi-label {
  flex-shrink: 0;
  min-width: 90px;
  color: #94a3b8;
}
.bi-value {
  color: #cbd5e1;
  word-break: break-all;
}
html:not(.dark) .bi-value {
  color: #334155;
}
.bi-value code {
  color: #a5b4fc;
}
.backend-actions {
  display: flex;
  gap: 10px;
  margin: 8px 0;
}

.update-result {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.up-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.04);
  font-size: 0.84rem;
  flex-wrap: wrap;
}
html:not(.dark) .up-row {
  background: rgba(15, 23, 42, 0.04);
}
.up-name {
  font-weight: 700;
  color: #e2e8f0;
  min-width: 90px;
}
html:not(.dark) .up-name {
  color: #1e293b;
}
.up-ver {
  color: #cbd5e1;
}
html:not(.dark) .up-ver {
  color: #334155;
}
.up-note {
  color: #94a3b8;
  font-size: 0.78rem;
}
.up-badge {
  font-weight: 700;
}
.up-badge.ok {
  color: #4ade80;
}
.up-badge.warn {
  color: #fbbf24;
}
.up-link {
  color: #818cf8;
  text-decoration: none;
  font-size: 0.78rem;
}

@media (max-width: 640px) {
  .setting-row {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
