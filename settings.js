import { defineStore } from 'pinia'
import i18n from '@/i18n'

const THEME_KEY = 'olmwed_theme'
const LOCALE_KEY = 'olmwed_locale'

/** Resolve the effective dark/light mode, honoring "system" preference. */
function resolveDark(theme) {
  if (theme === 'dark') return true
  if (theme === 'light') return false
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

/** Apply the current theme to the <html> element. */
function applyTheme(theme) {
  document.documentElement.classList.toggle('dark', resolveDark(theme))
}

let mediaQueryListener = null

/**
 * UI settings store: theme (dark / light / system) and locale (zh-CN / en-US).
 * Both are persisted to localStorage and applied globally.
 */
export const useSettingsStore = defineStore('settings', {
  state: () => ({
    theme: localStorage.getItem(THEME_KEY) || 'dark',
    locale: localStorage.getItem(LOCALE_KEY) || 'zh-CN',
  }),

  getters: {
    isDark: (state) => resolveDark(state.theme),
  },

  actions: {
    init() {
      this.applyTheme(this.theme)
      this.applyLocale(this.locale)
      // Follow OS theme changes while in "system" mode
      mediaQueryListener = (e) => {
        if (this.theme === 'system') applyTheme(this.theme)
      }
      window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', mediaQueryListener)
    },

    setTheme(theme) {
      this.theme = theme
      localStorage.setItem(THEME_KEY, theme)
      this.applyTheme(theme)
    },

    applyTheme(theme) {
      applyTheme(theme)
    },

    /** Quick toggle used by the topbar button (dark <-> light). */
    toggleTheme() {
      this.setTheme(this.isDark ? 'light' : 'dark')
    },

    setLocale(locale) {
      this.locale = locale
      localStorage.setItem(LOCALE_KEY, locale)
      this.applyLocale(locale)
    },

    applyLocale(locale) {
      i18n.global.locale.value = locale
      document.documentElement.lang = locale === 'en-US' ? 'en' : 'zh-CN'
    },
  },
})
