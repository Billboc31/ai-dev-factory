# T229 — Add one-click project deployment for end-to-end validation

**Source**: GitHub Issue #305

## Description

# Context

After AI Dev Factory finishes implementing a project, there is currently no standard workflow to deploy the generated application for functional validation.

Being able to deploy a project with a single action is essential for demonstrations and for the human validation loop before writing UI/non-regression tests.

# Goal

Add a deployment stage allowing a generated project to be deployed easily so it can be tested by a human.

# Description

Implement a first deployment workflow that:

- detects whether a project is deployable;
- executes the project's deployment pipeline;
- exposes the deployment status in the dashboard;
- stores deployment history and logs;
- returns the deployed application URL when successful.

The deployment should become a reusable platform capability so future project templates can integrate with it.

# Out of Scope

- Automatic production deployments.
- Blue/green or canary deployments.
- Rollback strategies.
- Multi-environment management.
- Automatic UI validation.
- Automatic creation of regression tests.

# Acceptance Criteria

- A project can be deployed from AI Dev Factory.
- Deployment progress is visible in the dashboard.
- Success and failure states are persisted.
- Deployment logs are available for troubleshooting.
- The deployed application's URL is stored and displayed.
- Deployment can be retried after a failure.
- Existing workflows remain unchanged when deployment is not used.
