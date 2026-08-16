<template>
  <div class="layout">
    <!-- Mobile off-canvas backdrop (only visible on small screens) -->
    <transition name="fade">
      <div v-if="!sidebarOpen" class="backdrop" @click="sidebarOpen = true"></div>
    </transition>

    <!-- ======================= Sidebar ======================= -->
    <aside class="sidebar glass" :class="{ 'sidebar-collapsed': !sidebarOpen }">
      <div class="brand">
        <div class="brand-logo">◆</div>
        <div class="brand-text">
          <div class="brand-name">{{ t('app.name') }}</div>
          <div class="brand-slogan">{{ t('app.slogan') }}</div>
        </div>
      </div>

      <nav class="nav">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          active-class="nav-item-active"
          @click="sidebarOpen = false"
        >
          <component :is="item.icon" class="nav-icon" />
          <span class="nav-label">{{ t(item.labelKey) }}</span>
        </router-link>
      </nav>

      <div class="sidebar-footer">
        <div class="backend-chip" :title="t('app.backendLabel')">
          <span class="backend-dot"></span>
          <span class="backend-text">{{ backendShort }}</span>
        </div>
        <div class="footer-right">
          <span class="ver">v0.1.0</span>
          <button
            class="sidebar-hide-btn"
            :title="t('app.hideSidebar')"
            @click="sidebarOpen = false"
          >
            ◀
          </button>
        </div>
      </div>
    </aside>

    <!-- ======================= Main column ======================= -->
    <div class="main">
      <header class="topbar">
        <button class="hamburger" aria-label="menu" @click="toggleSidebar">
          <IconMenu class="w-5 h-5" />
        </button>

        <h1 class="page-title">{{ t(pageTitleKey) }}</h1>

        <div class="topbar-actions">
          <!-- 模型后端状态 -->
          <span
            class="backend-indicator"
            :class="{ down: !backendOk }"
            :title="backendTitle"
          >
            <span class="bi-dot"></span>
          </span>

          <!-- Theme toggle -->
          <button
            class="icon-btn"
            :title="t('theme.title')"
            @click="settings.toggleTheme()"
          >
            <IconSun v-if="settings.isDark" class="w-5 h-5" />
            <IconMoon v-else class="w-5 h-5" />
          </button>

          <!-- Language switcher -->
          <select
            class="lang-select"
            :value="settings.locale"
            :title="t('language.title')"
            @change="onLocaleChange"
          >
            <option value="zh-CN">{{ t('language.zh') }}</option>
            <option value="en-US">{{ t('language.en') }}</option>
          </select>

          <!-- User -->
          <div class="user-chip">
            <span class="avatar">{{ initial }}</span>
            <span class="username hidden sm:inline">{{ auth.displayName }}</span>
            <button class="logout-btn" :title="t('common.logout')" @click="handleLogout">
              <IconLogout class="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      <main class="content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import api from '@/api'
import { useAuthStore } from '@/stores/auth'
import { useSettingsStore } from '@/stores/settings'
import {
  IconBolt,
  IconBook,
  IconChat,
  IconCog,
  IconCube,
  IconLogout,
  IconMenu,
  IconMoon,
  IconSun,
} from '@/components/icons'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const settings = useSettingsStore()

// 桌面端默认展开侧边栏；移动端默认收起（点击汉堡展开）。
// 用户开关状态持久化到 localStorage（导航栏显示/隐藏开关）。
const saved = localStorage.getItem('olmwed_sidebar_open')
const sidebarOpen = ref(saved !== null ? saved === '1' : window.innerWidth >= 768)
const systemInfo = ref(null)

function toggleSidebar() {
  sidebarOpen.value = !sidebarOpen.value
  localStorage.setItem('olmwed_sidebar_open', sidebarOpen.value ? '1' : '0')
}

const navItems = [
  { path: '/chat', labelKey: 'nav.chat', icon: IconChat },
  { path: '/knowledge', labelKey: 'nav.knowledge', icon: IconBook },
  { path: '/models', labelKey: 'nav.models', icon: IconCube },
  { path: '/api', labelKey: 'nav.api', icon: IconBolt },
  { path: '/settings', labelKey: 'nav.settings', icon: IconCog },
]

const pageTitleKey = computed(() => route.meta.titleKey || 'app.name')
const initial = computed(() => (auth.displayName || '?').charAt(0).toUpperCase())
const backendShort = computed(() => {
  const label = systemInfo.value?.backend_label || ''
  if (!label) return ''
  return label.includes('OpenAI') ? 'ollama.cpp' : 'Ollama'
})

// 后端实时状态（轮询 /api/system/status）
const backendOk = ref(true)
const backendModels = ref(0)
const backendLoaded = ref(0)
const backendTitle = computed(() => {
  if (!backendOk.value) return t('chat.backendDown')
  return `${systemInfo.value?.backend_label || ''} · ${backendModels.value} 模型 / ${backendLoaded.value} 已加载`
})

let statusTimer = null
async function refreshStatus() {
  try {
    const { data } = await api.get('/system/status')
    backendOk.value = !!data.backend_ok
    backendModels.value = data.models || 0
    backendLoaded.value = data.loaded || 0
    if (data.backend_label) systemInfo.value = { ...(systemInfo.value || {}), backend_label: data.backend_label }
  } catch (e) {
    backendOk.value = false
  }
}

onMounted(async () => {
  try {
    const { data } = await api.get('/system/info')
    systemInfo.value = data
  } catch (e) {
    /* non-fatal */
  }
  refreshStatus()
  statusTimer = setInterval(refreshStatus, 30000)
})

onUnmounted(() => {
  if (statusTimer) clearInterval(statusTimer)
})

function onLocaleChange(e) {
  settings.setLocale(e.target.value)
}

function handleLogout() {
  auth.logout()
  router.replace('/login')
}
</script>

<style scoped>
.layout {
  height: 100vh;
  display: flex;
  overflow: hidden;
  background: linear-gradient(180deg, #0b1220 0%, #0f172a 55%, #0b1220 100%);
}
html:not(.dark) .layout {
  background: linear-gradient(180deg, #f8fafc 0%, #eef2f7 55%, #f8fafc 100%);
}

/* ---------------- Sidebar ---------------- */
.sidebar {
  flex-shrink: 0;
  width: 228px;
  height: 100%;
  display: flex;
  flex-direction: column;
  border-radius: 0;
  border-right: 1px solid rgba(255, 255, 255, 0.12);
  transition: margin-left 0.25s ease, transform 0.25s ease;
}
html:not(.dark) .sidebar {
  border-right-color: rgba(15, 23, 42, 0.08);
}
/* 桌面端：收起 = 向左移出（不占布局空间） */
.sidebar-collapsed {
  margin-left: -228px;
}

.sidebar-footer {
  padding: 12px 14px 14px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
html:not(.dark) .sidebar-footer {
  border-top-color: rgba(15, 23, 42, 0.08);
}
.footer-right {
  display: flex;
  align-items: center;
  gap: 6px;
}
.ver {
  font-size: 0.7rem;
  color: #64748b;
}
.sidebar-hide-btn {
  width: 24px;
  height: 24px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 7px;
  font-size: 0.7rem;
  color: #94a3b8;
  background: transparent;
  cursor: pointer;
}
.sidebar-hide-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #e2e8f0;
}
html:not(.dark) .sidebar-hide-btn:hover {
  background: rgba(15, 23, 42, 0.08);
  color: #1e293b;
}
.backend-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 0.7rem;
  color: #94a3b8;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
}
html:not(.dark) .backend-chip {
  background: rgba(15, 23, 42, 0.05);
  border-color: rgba(15, 23, 42, 0.1);
}
.backend-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #4ade80;
}
.backend-text {
  white-space: nowrap;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 22px 20px 18px;
}
.brand-logo {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  color: #fff;
  font-size: 1.05rem;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  box-shadow: 0 8px 20px rgba(99, 102, 241, 0.4);
}
.brand-name {
  font-size: 1rem;
  font-weight: 700;
  color: #f1f5f9;
  letter-spacing: 0.02em;
}
html:not(.dark) .brand-name {
  color: #1e293b;
}
.brand-slogan {
  margin-top: 2px;
  font-size: 0.68rem;
  color: #94a3b8;
}

.nav {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px 12px;
  overflow-y: auto;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 11px 14px;
  border-radius: 12px;
  font-size: 0.92rem;
  font-weight: 500;
  color: #94a3b8;
  text-decoration: none;
  transition: all 0.15s ease;
}
.nav-item:hover {
  color: #e2e8f0;
  background: rgba(255, 255, 255, 0.08);
}
html:not(.dark) .nav-item:hover {
  color: #1e293b;
  background: rgba(15, 23, 42, 0.06);
}
.nav-icon {
  width: 20px;
  height: 20px;
}
.nav-item-active {
  color: #fff;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.9), rgba(139, 92, 246, 0.85));
  box-shadow: 0 6px 16px rgba(99, 102, 241, 0.35);
}
.nav-item-active:hover {
  color: #fff;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.9), rgba(139, 92, 246, 0.85));
}

/* ---------------- Main ---------------- */
.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  height: 100%;
}

.topbar {
  height: 60px;
  margin: 12px 16px 0;
  padding: 0 16px;
  display: flex;
  align-items: center;
  gap: 14px;
  border-radius: 14px;
  backdrop-filter: blur(20px);
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
  box-shadow: 0 8px 24px rgba(2, 6, 23, 0.2);
}
html:not(.dark) .topbar {
  background: rgba(255, 255, 255, 0.65);
  border-color: rgba(15, 23, 42, 0.08);
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
}

.hamburger {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 10px;
  border: none;
  color: #cbd5e1;
  background: transparent;
  cursor: pointer;
}
.hamburger:hover {
  background: rgba(255, 255, 255, 0.1);
}

.page-title {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 600;
  color: #e2e8f0;
}
html:not(.dark) .page-title {
  color: #1e293b;
}

.topbar-actions {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 10px;
}

.icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 10px;
  color: #cbd5e1;
  background: transparent;
  cursor: pointer;
  transition: background 0.15s ease;
}
.icon-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}
html:not(.dark) .icon-btn {
  color: #475569;
}
html:not(.dark) .icon-btn:hover {
  background: rgba(15, 23, 42, 0.08);
  color: #1e293b;
}

.lang-select {
  height: 36px;
  padding: 0 8px;
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 10px;
  font-size: 0.8rem;
  color: #cbd5e1;
  background: rgba(255, 255, 255, 0.06);
  outline: none;
  cursor: pointer;
}
html:not(.dark) .lang-select {
  color: #334155;
  border-color: rgba(15, 23, 42, 0.15);
  background: rgba(255, 255, 255, 0.8);
}
.lang-select option {
  color: #1e293b;
}

/* 后端状态指示 */
.backend-indicator {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 9px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.05);
  cursor: default;
}
.bi-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #4ade80;
  box-shadow: 0 0 8px rgba(74, 222, 128, 0.7);
}
.backend-indicator.down .bi-dot {
  background: #f87171;
  box-shadow: 0 0 8px rgba(248, 113, 113, 0.7);
}

.user-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 6px 4px 4px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.05);
}
html:not(.dark) .user-chip {
  border-color: rgba(15, 23, 42, 0.12);
  background: rgba(15, 23, 42, 0.04);
}
.avatar {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 9px;
  font-size: 0.8rem;
  font-weight: 700;
  color: #fff;
  background: linear-gradient(135deg, #6366f1, #22d3ee);
}
.username {
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.82rem;
  color: #cbd5e1;
}
html:not(.dark) .username {
  color: #334155;
}
.logout-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 8px;
  color: #94a3b8;
  background: transparent;
  cursor: pointer;
}
.logout-btn:hover {
  color: #f87171;
  background: rgba(248, 113, 113, 0.12);
}

/* ---------------- Content ---------------- */
.content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

/* ---------------- Mobile ---------------- */
.backdrop {
  position: fixed;
  inset: 0;
  z-index: 40;
  background: rgba(2, 6, 23, 0.5);
  backdrop-filter: blur(2px);
}
/* 桌面端不需要遮罩 */
@media (min-width: 768px) {
  .backdrop {
    display: none;
  }
}

@media (max-width: 767px) {
  .sidebar {
    position: fixed;
    top: 0;
    left: 0;
    bottom: 0;
    z-index: 50;
    margin-left: 0;
    transform: translateX(-100%);
    transition: transform 0.25s ease;
  }
  /* 移动端：非收起状态 = 展开（滑入） */
  .sidebar:not(.sidebar-collapsed) {
    transform: translateX(0);
  }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
