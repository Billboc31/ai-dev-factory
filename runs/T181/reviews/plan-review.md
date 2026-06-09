# T181 — Plan Review

## Verdict

The plan is good and aligned with the intended pivot: move AI Dev Factory from an environment-centric/deployer-centric tool toward a project-centric multi-project workspace.

The scope is correctly focused on:

- importing existing projects;
- registering projects in a workspace;
- creating isolated per-project runtime directories;
- starting/stopping one supervisor/daemon runtime per project;
- enabling the ticket/dev loop without requiring deployment.

This is the right foundation for bootstrapping an existing project such as the personal RAG project and using AI Dev Factory to work on it.

## Strong points

- Deployment, Traefik and healthchecks are explicitly out of scope.
- The plan introduces a persistent workspace registry instead of relying only on directory scanning.
- Imported projects get their own runtime tree.
- Per-project daemon isolation is addressed at the supervisor level.
- The UI starts with a simple Projects page and Import wizard, which is the right MVP.
- The ticket/dev workflow remains part of the acceptance criteria.

## Main risks

### Project ID safety

`project_id` must be strictly normalized and validated before it is used in filesystem paths.

Without strict validation, runtime paths can become unsafe or inconsistent.

### Runtime ownership

The implementation must avoid silently reusing the global AI Dev Factory runtime directories.

Every imported project must resolve to its own runtime root.

### Daemon lifecycle complexity

Per-project daemon state must not reuse the existing single-daemon globals accidentally. The implementation should make it obvious whether a daemon belongs to the global/dev runtime or to a specific project.

### Ticket collisions

The plan excludes duplicate ticket collision prevention across projects. That is acceptable for the MVP, but it should be tracked as a follow-up because ticket IDs such as `T181` may exist in several projects.

## Recommendation

Proceed with the plan, but add a small required fix before implementation: strict `project_id` normalization/validation and explicit runtime-root logging for every per-project daemon operation.