import { request } from './http'

export const getMessages = (params) => request(`/api/messages?${new URLSearchParams(params).toString()}`)
export const createMessage = (content) => request('/api/messages', {
  method: 'POST',
  headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  body: `content=${encodeURIComponent(content)}`,
})

export const getUsers = () => request('/api/users')
export const createUser = (form) => request('/api/users', {
  method: 'POST',
  headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  body: new URLSearchParams(form).toString(),
})

export const getMetrics = () => request('/api/metrics')
export const getHealth = () => request('/api/health')

export const getBackups = () => request('/api/backups')
export const createBackup = (note) => request('/api/backups', {
  method: 'POST',
  headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  body: `note=${encodeURIComponent(note)}`,
})
export const restoreBackup = (id) => request(`/api/backups/${id}/restore`, { method: 'POST' })

export const getLogs = (filename, limit) => request(`/api/logs?filename=${filename}&limit=${limit}`)
