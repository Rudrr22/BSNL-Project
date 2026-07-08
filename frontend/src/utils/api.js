import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const WS_BASE_URL = API_BASE_URL.replace(/^http/, 'ws')

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 20000,
})

export const endpoints = {
  health: () => api.get('/health'),
  stats: () => api.get('/api/stats'),
  recentLogs: (limit = 50) => api.get('/api/logs/recent', { params: { limit } }),
  anomalies: (params = {}) => api.get('/api/anomalies', { params }),
  acknowledge: (id) => api.patch('/api/anomalies/' + id + '/acknowledge'),
  analyses: () => api.get('/api/analyses'),
  analysis: (id) => api.get('/api/analyses/' + id),
  uploadLogs: (file) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/api/logs/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  chat: (payload) => api.post('/api/chat', payload),
  ragStats: () => api.get('/api/chat/stats'),
}

export function logsSocketUrl() {
  return WS_BASE_URL + '/ws/logs'
}

export function getApiBaseUrl() {
  return API_BASE_URL
}
