import axios from 'axios'

const client = axios.create({ baseURL: '/api' })

export const listBranches = (projectId) => client.get(`/projects/${projectId}/branches`)

export const listProjects = () => client.get('/projects')

export const importProject = (projectRoot, projectId) =>
  client.post('/projects/import', { project_root: projectRoot, project_id: projectId })

export const deleteProject = (projectId) => client.delete(`/projects/${projectId}`)

export const getProject = (projectId) =>
  listProjects().then(res => {
    const project = res.data.find(p => p.name === projectId)
    return { data: project ?? null }
  })

// Agent layout — async job (returns { ok, job_id })
export const startAgentLayout = (projectId) =>
  client.post(`/projects/${projectId}/install-agent-layout`, {})

export const getAgentLayoutLatest = (projectId) =>
  client.get(`/projects/${projectId}/install-agent-layout/latest`)

export const getAgentLayoutJob = (projectId, jobId) =>
  client.get(`/projects/${projectId}/install-agent-layout/${jobId}`)

export const getAgentLayoutLogs = (projectId, jobId, offset = 0) =>
  client.get(`/projects/${projectId}/install-agent-layout/${jobId}/logs`, { params: { offset } })

export const getAgentLayoutFiles = (projectId, jobId) =>
  client.get(`/projects/${projectId}/install-agent-layout/${jobId}/files`)

export const getAgentLayoutFile = (projectId, jobId, path) =>
  client.get(`/projects/${projectId}/install-agent-layout/${jobId}/file`, { params: { path } })

export const getAgentLayoutStatus = (projectId) =>
  client.get(`/projects/${projectId}/install-agent-layout/status`)
