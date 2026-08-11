import axios from 'axios'

const client = axios.create({ baseURL: '/api' })

const base = (projectId) =>
  projectId
    ? `/projects/${projectId}/dispatcher/batches`
    : '/dispatcher/batches'

export const listBatches = (projectId) => client.get(base(projectId))

export const getCurrentNextBatch = (projectId) =>
  client.get(`${base(projectId)}/current`)

export const getBatch = (projectId, batchId) =>
  client.get(`${base(projectId)}/${batchId}`)

export const getBatchGraph = (projectId, batchId) =>
  client.get(`${base(projectId)}/${batchId}/graph`)

export const getBatchPhases = (projectId, batchId) =>
  client.get(`${base(projectId)}/${batchId}/phases`)

export const getBatchInsights = (projectId, batchId) =>
  client.get(`${base(projectId)}/${batchId}/insights`)

export const freezeBatch = (projectId, batchId) =>
  client.post(`${base(projectId)}/${batchId}/freeze`)

export const retryBatchDependencyAnalysis = (projectId, batchId) =>
  client.post(`${base(projectId)}/${batchId}/retry-dependency-analysis`)

export const recomputeBatchDependencies = (projectId, batchId) =>
  client.post(`${base(projectId)}/${batchId}/recompute-dependencies`)

export const cancelBatch = (projectId, batchId) =>
  client.post(`${base(projectId)}/${batchId}/cancel`)

export const getBatchPipelineStatus = (projectId, batchId) =>
  client.get(`${base(projectId)}/${batchId}/pipeline-status`)
