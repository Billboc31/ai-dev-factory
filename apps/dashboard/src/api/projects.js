import axios from 'axios'

const client = axios.create({ baseURL: '/api' })

export const listBranches = (projectId) => client.get(`/projects/${projectId}/branches`)
