import { defineStore } from 'pinia'
import api from '@/api'

/** Authentication store: holds the JWT and the current user profile. */
export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('olmwed_token') || '',
    user: JSON.parse(localStorage.getItem('olmwed_user') || 'null'),
  }),

  getters: {
    isAuthenticated: (state) => !!state.token,
    displayName: (state) => state.user?.username || 'unknown',
  },

  actions: {
    async login(username, password) {
      const { data } = await api.post('/auth/login', { username, password })
      this.token = data.access_token
      this.user = data.user
      localStorage.setItem('olmwed_token', data.access_token)
      localStorage.setItem('olmwed_user', JSON.stringify(data.user))
    },

    logout() {
      this.token = ''
      this.user = null
      localStorage.removeItem('olmwed_token')
      localStorage.removeItem('olmwed_user')
    },
  },
})
