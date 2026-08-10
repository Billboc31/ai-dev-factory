import axios from 'axios'

const client = axios.create({ baseURL: '/api' })

export const postWorkspaceMessage = (projectId, message, history) =>
  client.post(`/projects/${projectId}/workspace/chat`, {
    message,
    conversation_history: history,
  })

export const confirmWorkspaceAction = (projectId, actionId) =>
  client.post(`/projects/${projectId}/workspace/actions/confirm`, {
    action_id: actionId,
  })

export const confirmWorkspaceIssue = (projectId, draftId) =>
  client.post(`/projects/${projectId}/workspace/issues/confirm`, {
    draft_id: draftId,
  })

export const getDeploymentStatus = (projectId, deploymentId) =>
  client.get(`/projects/${projectId}/workspace/deployments/${deploymentId}`)

export const deployProject = (projectId) =>
  client.post(`/projects/${projectId}/workspace/deploy`)

export const getDeployStatus = (projectId, deploymentId) =>
  client.get(`/projects/${projectId}/workspace/deploy/${deploymentId}`)

export const getDeployHistory = (projectId) =>
  client.get(`/projects/${projectId}/workspace/deploy/history`)
