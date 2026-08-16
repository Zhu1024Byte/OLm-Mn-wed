import axios from 'axios'

/**
 * Shared Axios instance for the OLm-Mn-wed JSON API.
 * - attaches the JWT from localStorage to every request
 * - on 401, clears the session and redirects to the login page
 */
const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('olmwed_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('olmwed_token')
      localStorage.removeItem('olmwed_user')
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  },
)

export default api
