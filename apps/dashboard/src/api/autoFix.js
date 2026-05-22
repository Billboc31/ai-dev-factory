import axios from 'axios'

const client = axios.create({ baseURL: '/api' })

export const proposeAutoFix = (projectId, sandboxId, failingStep, execCmd) =>
  client.post(`/projects/${projectId}/auto-fix/propose`, {
    sandbox_id: sandboxId,
    failing_step: failingStep ?? null,
    exec_cmd: execCmd,
  })

export const getProposal = (projectId, proposalId) =>
  client.get(`/projects/${projectId}/auto-fix/proposal/${proposalId}`)

export const listProposals = (projectId) =>
  client.get(`/projects/${projectId}/auto-fix/proposals`)

export const startAutoFixLoop = (projectId, { execCmd, sandboxId, maxRetries, failingStep }) =>
  client.post(`/projects/${projectId}/auto-fix/loop/start`, {
    exec_cmd: execCmd,
    sandbox_id: sandboxId ?? null,
    max_retries: maxRetries ?? 3,
    failing_step: failingStep ?? null,
  })

export const getAutoFixSession = (projectId, sessionId) =>
  client.get(`/projects/${projectId}/auto-fix/loop/${sessionId}`)

export const listAutoFixSessions = (projectId) =>
  client.get(`/projects/${projectId}/auto-fix/loops`)
