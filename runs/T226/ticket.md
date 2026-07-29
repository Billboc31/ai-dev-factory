# T226 — Add floating and dockable AI Workspace window

**Source**: GitHub Issue #310

## Description

## Objective

Enhance the AI Workspace by replacing the fixed chat panel with a movable, resizable and dockable window, providing an IDE-like experience.

## Context

The AI Workspace should remain available while navigating through the project, but users should be free to organize their workspace according to their preferences.

## Requirements

- Support a floating window mode.
- Allow drag & drop using the window header.
- Allow resizing from edges and corners.
- Support docking to the left and right sides.
- Allow switching back to floating mode at any time.
- Preserve the current conversation while changing modes.
- Persist the selected mode, size and position between sessions.
- Prevent the window from being moved completely off-screen.
- Define sensible minimum dimensions.
- Adapt automatically to smaller screens (drawer or full-screen mode).
- Ensure the workspace remains available across project navigation.

## Acceptance criteria

- The AI Workspace can be moved freely.
- The window can be resized interactively.
- Users can dock and undock the workspace.
- Position and dimensions are restored after a page refresh.
- Navigation inside AI Dev Factory does not reset the workspace.
- The experience remains responsive and accessible.

## Out of scope

- Multiple simultaneous workspace windows.
- Tabbed conversations.
- Multi-monitor specific behaviors.
