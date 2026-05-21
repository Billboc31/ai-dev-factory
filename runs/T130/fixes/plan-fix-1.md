# Plan fix request — T130

Please update the architecture so AI project analysis runs through the host supervisor.

Required architecture:

Dashboard
→ Control API
→ Host supervisor
→ Host-side analysis worker
→ Git branch and PR

## Include in revised plan

- Add supervisor endpoints for analysis jobs.
- Supervisor launches the analysis worker host-side.
- Analysis worker uses the configured host AI runtime.
- Analysis worker has access to gh, git worktrees, host credentials and canonical runtime paths.
- Control API only triggers analysis, polls status, reads logs and exposes PR URLs.
- Analysis status and logs remain visible in the dashboard.
- Generated files are still committed and pushed from the host runtime.

## Exclude

- Direct LLM execution from Docker control API.
- Docker-side git branch creation.
- Docker-side PR creation.

## Acceptance criteria update

- Analysis jobs execute host-side through the supervisor.
- Generated files are committed using the host git runtime.
- PR creation uses the host gh runtime.
- Dashboard still provides analysis visibility.
- Existing supervisor and daemon architecture stays consistent.
