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
