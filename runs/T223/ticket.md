# T223 — Add project-level option to disable human plan approval gate

**Source**: GitHub Issue #303

## Description

# Context

For production projects, requiring a human to approve the implementation plan before coding starts is an important safety mechanism.

For demos and fully automated showcase projects, however, this approval step slows the pipeline considerably because every ticket waits for manual intervention before implementation.

We need a project-level option allowing demo projects to automatically continue after plan generation while keeping the current behaviour as the default.

# Goal

Add a project runtime setting that enables or disables the Human Plan Approval gate.

Default behaviour must remain unchanged.

# New project setting

```text
PROJECT_REQUIRE_HUMAN_PLAN_APPROVAL
```

Default:

```text
true
```

Demo configuration:

```text
false
```

# Behaviour

## When enabled (default)

Current behaviour:

```text
Plan generated
↓
Waiting for human plan approval
↓
Approve
↓
Implementation
```

## When disabled

```text
Plan generated
↓
Automatically approved
↓
Implementation can continue immediately
```

The system should still persist the generated plan and mark it as auto-approved for auditability.

# Scope

This setting ONLY affects the Human Plan Approval gate.

It must NOT bypass:

- Ticket Intelligence
- Global Dependency Analysis
- Readiness
- Dispatcher scheduling
- Human execution approval (if enabled separately)
- Tests
- CI

# Runtime settings

The option should be configurable:

- per project
- through the existing Global/Project Settings UI
- without requiring a code change
- applied dynamically after configuration reload

# UI

Add a checkbox in Project Settings:

```text
☑ Require Human Plan Approval
```

Help text:

```text
When disabled, implementation plans are automatically approved after generation. Useful for demos and fully automated projects.
```

# Audit

When auto-approved, record clearly:

```text
approval_type = AUTO
approval_reason = PROJECT_SETTING
approved_by = SYSTEM
```

The UI should display that the approval was automatic rather than manual.

# Acceptance criteria

- New project-level runtime setting exists.
- Default value is true.
- Setting can be changed from Project Settings.
- Changing the setting does not require restarting the application.
- When disabled, tickets do not wait for manual plan approval.
- The generated plan is still persisted.
- Automatic approvals are distinguishable from manual approvals in the UI and database.
- All other workflow gates remain unchanged.
- Existing projects continue to behave exactly as before by default.
