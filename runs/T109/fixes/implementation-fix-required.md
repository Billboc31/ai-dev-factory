# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

## Decision

`IMPLEMENTATION_FIX_REQUIRED`

## Blocking issue

T109 introduces `tools/agent_runner/runtime_checkpoint.py`, but the migration is incomplete.

`run_daemon.py::_ensure_clean_working_tree()` still uses the old ad-hoc persistence path:

```python
subprocess.run([sys.executable, str(RUN_TICKET), ticket_id, "--commit", "--include-code"])
...
subprocess.run([sys.executable, str(RUN_TICKET), ticket_id, "--push"])
```

This keeps the exact class of bugs T109 is supposed to remove:

- persistence logic duplicated outside `runtime_checkpoint.py`
- checkpoint potentially executed from the wrong cwd
- dirty tree may remain after commit/push
- push failures are not centralized
- runtime transitions can continue using legacy persistence behavior

## Required fix

Replace the old subprocess-based checkpoint path in `_ensure_clean_working_tree()` with `checkpoint_transition()`.

### Expected behavior

When dirty files are only workflow artifacts and/or code-scope files:

```text
pre-flight dirty tree
→ checkpoint_transition(ticket_id, message, push=auto_push, include_code=True, cwd=<ticket cwd>)
→ verify clean tree
→ continue only if checkpoint succeeds
```

When unknown files are present:

```text
abort safely
```

### Implementation guidance

1. Update `_ensure_clean_working_tree()` signature if needed so it can receive `cwd`:

```python
def _ensure_clean_working_tree(ticket_id: str, auto_push: bool = False, cwd: str | None = None) -> bool:
```

2. Ensure dirty classification runs in the same cwd as the ticket worktree.

If `_classify_dirty_files()` currently runs only in the process cwd, either:

- add a `cwd` parameter to `_classify_dirty_files(ticket_id, cwd=None)`, and run `git status --porcelain` with `cwd=cwd`, or
- ensure `_ensure_clean_working_tree()` is only called from the correct cwd.

Preferred: make both helpers explicitly `cwd`-aware.

3. Replace the old commit/push block with:

```python
try:
    checkpoint_transition(
        ticket_id,
        f"{ticket_id}: pre-flight checkpoint — persist dirty runtime artifacts",
        push=auto_push,
        include_code=True,
        cwd=cwd,
    )
except CheckpointError as exc:
    _log(f"{ticket_id}: pre-flight abort — checkpoint failed: {exc}")
    return False
except DirtyTreeError as exc:
    _log(f"{ticket_id}: DIRTY_RUNTIME_CHECKPOINT — pre-flight: {exc}")
    return False
```

4. In `launch_ticket()`, pass the worktree cwd when launching from a worktree:

```python
if not _ensure_clean_working_tree(ticket_id, auto_push=auto_push, cwd=str(worktree_path)):
    return
```

For legacy mode:

```python
if not _ensure_clean_working_tree(ticket_id, auto_push=auto_push, cwd=None):
    return
```

5. Remove old `run_ticket.py --commit` / `run_ticket.py --push` subprocess usage from `_ensure_clean_working_tree()`.

## Tests required

Update or add tests proving:

1. `_ensure_clean_working_tree()` calls `checkpoint_transition()` instead of `run_ticket.py --commit`.
2. Worktree cwd is passed through to dirty classification/checkpoint.
3. `DirtyTreeError` produces a clear `DIRTY_RUNTIME_CHECKPOINT` log and returns `False`.
4. `CheckpointError` returns `False` and does not continue the worker.
5. Unknown dirty files still abort without checkpoint.

## Non-blocking cleanup

After this fix, search for remaining ad-hoc persistence paths:

```bash
grep -R "--commit" -n tools/agent_runner services tests
grep -R "--push" -n tools/agent_runner services tests
grep -R "git commit" -n tools/agent_runner services tests
```

Some CLI commands may remain for direct user operations, but runtime transitions should use `checkpoint_transition()`.

## Expected final decision after fix

If this migration is completed and tests pass, T109 should be eligible for `IMPLEMENTATION_APPROVED`.
