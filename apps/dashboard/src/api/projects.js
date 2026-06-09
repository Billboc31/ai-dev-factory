import axios from 'axios'

const client = axios.create({ baseURL: '/api' })

export const listBranches = (projectId) => client.get(`/projects/${projectId}/branches`)

export const listProjects = () => client.get('/projects')

export const importProject = (projectRoot, projectId) =>
  client.post('/projects/import', { project_root: projectRoot, project_id: projectId })

export const deleteProject = (projectId) => client.delete(`/projects/${projectId}`)
