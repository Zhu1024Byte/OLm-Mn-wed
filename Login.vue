<template>
  <div class="login-page">
    <div class="login-card glass-card fade-in">
      <div class="brand">
        <div class="brand-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <path d="M12 2 2 7l10 5 10-5-10-5Z" stroke-linejoin="round" />
            <path d="m2 12 10 5 10-5" stroke-linejoin="round" />
            <path d="m2 17 10 5 10-5" stroke-linejoin="round" />
          </svg>
        </div>
        <h1 class="brand-title">OLm-Mn-wed</h1>
        <p class="brand-subtitle">Local AI Model WebUI</p>
      </div>

      <form class="login-form" @submit.prevent="handleLogin">
        <div class="field">
          <label for="username">{{ t('common.username') }}</label>
          <input
            id="username"
            v-model.trim="username"
            class="glass-input"
            type="text"
            autocomplete="username"
            :placeholder="t('login.usernamePlaceholder')"
            required
          />
        </div>

        <div class="field">
          <label for="password">{{ t('common.password') }}</label>
          <input
            id="password"
            v-model="password"
            class="glass-input"
            type="password"
            autocomplete="current-password"
            :placeholder="t('login.passwordPlaceholder')"
            required
          />
        </div>

        <p v-if="error" class="error">{{ error }}</p>

        <button class="login-btn" type="submit" :disabled="loading">
          <span v-if="loading" class="spinner"></span>
          {{ loading ? t('common.loading') : t('common.login') }}
        </button>
      </form>

      <p class="hint">
        {{ t('login.hint') }}
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const { t } = useI18n()
const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function handleLogin() {
  error.value = ''
  loading.value = true
  try {
    await auth.login(username.value, password.value)
    router.replace(route.query.redirect || '/')
  } catch (e) {
    error.value = e.response?.data?.detail || t('login.fail')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  overflow: hidden;
  background: linear-gradient(160deg, #0b1220 0%, #111827 60%, #0b1220 100%);
}

.login-card {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 400px;
  padding: 2.75rem 2.25rem 1.75rem;
  text-align: center;
}

.brand-icon {
  width: 56px;
  height: 56px;
  margin: 0 auto 0.75rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 16px;
  color: #fff;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  box-shadow: 0 10px 30px rgba(99, 102, 241, 0.45);
}
.brand-icon svg {
  width: 28px;
  height: 28px;
}

.brand-title {
  margin: 0;
  font-size: 1.6rem;
  font-weight: 700;
  letter-spacing: 0.02em;
  color: #f8fafc;
}
.brand-subtitle {
  margin: 0.25rem 0 0;
  font-size: 0.85rem;
  color: #94a3b8;
}

.login-form {
  margin-top: 2rem;
  text-align: left;
}
.field {
  margin-bottom: 1.1rem;
}
.field label {
  display: block;
  margin-bottom: 0.4rem;
  font-size: 0.8rem;
  font-weight: 500;
  color: #cbd5e1;
}

.error {
  margin: 0.25rem 0 0.75rem;
  font-size: 0.8rem;
  color: #f87171;
}

.login-btn {
  width: 100%;
  margin-top: 0.5rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  border: none;
  border-radius: 0.75rem;
  font-size: 0.95rem;
  font-weight: 600;
  color: #fff;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  box-shadow: 0 8px 24px rgba(99, 102, 241, 0.4);
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.15s ease, opacity 0.15s ease;
}
.login-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 12px 28px rgba(99, 102, 241, 0.5);
}
.login-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.spinner {
  width: 15px;
  height: 15px;
  border: 2px solid rgba(255, 255, 255, 0.35);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.hint {
  margin: 1.5rem 0 0;
  font-size: 0.75rem;
  color: #64748b;
}
.hint code {
  color: #a5b4fc;
}
</style>
