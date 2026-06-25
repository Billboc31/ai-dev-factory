import axios from 'axios'

const client = axios.create({ baseURL: '/api' })

export const listSettings = () => client.get('/settings')

export const getSetting = (key) => client.get(`/settings/${encodeURIComponent(key)}`)

export const updateSetting = (key, value, updatedBy = null) =>
  client.put(`/settings/${encodeURIComponent(key)}`, {
    value,
    updated_by: updatedBy,
  })

export const resetSetting = (key) =>
  client.delete(`/settings/${encodeURIComponent(key)}`)
