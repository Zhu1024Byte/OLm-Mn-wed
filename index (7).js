import { createI18n } from 'vue-i18n'
import zhCN from './locales/zh-CN'
import enUS from './locales/en-US'

/**
 * vue-i18n instance.
 * - legacy: false  -> composition API mode (useI18n() / $t)
 * - globalInjection: true -> $t available in templates without setup()
 */
const i18n = createI18n({
  legacy: false,
  globalInjection: true,
  locale: localStorage.getItem('olmwed_locale') || 'zh-CN',
  fallbackLocale: 'zh-CN',
  messages: {
    'zh-CN': zhCN,
    'en-US': enUS,
  },
})

export default i18n
