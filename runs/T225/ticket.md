# T225 — Add persistent AI Project Workspace with controlled capabilities

**Source**: GitHub Issue #308

## Description

# Context

AI Dev Factory should provide a persistent AI workspace available from every project page, similar to Cursor's chat experience. However, it must not become a replacement for the AI Dev Factory workflow.

The AI should help users operate and understand the project, while preserving the principle that all functional development goes through GitHub issues and the existing pipeline.

**Every request issued from this workspace must be handled by the Supervisor.** The AI workspace is only a conversational interface; it never performs actions directly.

# Goal

Introduce a persistent AI workspace attached to each project that can answer questions, diagnose problems and execute controlled project actions through the Supervisor.

# Architecture

- The AI Workspace sends every user request to the Supervisor.
- The Supervisor decides whether the request is informational or actionable.
- Only the Supervisor is allowed to invoke platform capabilities.
- The AI Workspace never bypasses the Supervisor or directly calls internal services.

# Allowed capabilities

The AI may:

- Explain project status.
- Explain ticket states and workflow decisions.
- Diagnose blocked tickets.
- Analyze logs and test failures.
- Search project documentation.
- Read repository files.
- Explain configuration files.
- Create GitHub issues from user requests.
- Request project actions (resume execution, rerun intelligence, rerun dependency analysis, deployments, etc.), which are executed by the Supervisor after validation.

# Forbidden capabilities

The AI must NOT:

- Implement new features directly.
- Generate production code instead of creating an issue.
- Modify business source code.
- Bypass the GitHub Issue -> AI Dev Factory workflow.
- Bypass the Supervisor.
- Automatically create commits or pull requests for functional changes.

If the user requests a new feature or bug fix, the AI should propose creating a GitHub issue instead of editing the code.

# Acceptance Criteria

- Every project has its own persistent AI workspace.
- The workspace remains available while navigating through the project.
- The AI automatically receives the current project context.
- Every action requested from the workspace is routed through the Supervisor.
- Functional development requests are redirected to GitHub issue creation.
- Only explicitly allowed actions can be executed by the Supervisor on behalf of the AI.
