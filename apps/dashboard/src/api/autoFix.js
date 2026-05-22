import axios from 'axios'

const client = axios.create({ baseURL: '/api' })

export const proposeAutoFix = (projectId, sandboxId, failingStep, execCmd) =>
  client.post(`/projects/${projectId}/auto-fix/propose`, {
    sandbox_id: sandboxId,
    failing_step: failingStep ?? null,
    exec_cmd: execCmd ?? 'claude --dangerously-skip-permissions',
  })

export const getProposal = (projectId, proposalId) =>
  client.get(`/projects/${projectId}/auto-fix/proposal/${proposalId}`)

export const listProposals = (projectId) =>
  client.get(`/projects/${projectId}/auto-fix/proposals`)
