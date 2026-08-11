# Generic Conflict Resolver Task

Read `conflict/context.md` in the run directory. It contains the full ticket context, plan, reviews, PR diff, conflicted files (with conflict markers), and the latest commits on main.

Your task:
1. Edit every conflicted file in-place to remove all conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`).
2. Resolve each conflict by preserving both the ticket intent and the latest main behavior where possible.
3. Do not blindly pick ours or theirs — reason through each conflict.
4. Write your output (stdout) as `conflict/resolution.md` summarising every conflict decision.

ORM / Drizzle migrations (hard rules — common failure mode when coding in parallel):
- Keep migrations that already exist on **main** unchanged (SQL + their `meta/NNNN_snapshot.json`).
- If this ticket also created `NNNN_*.sql` and main already has a different `NNNN_*.sql`, **renumber the ticket migration** to `max(main)+1` (e.g. main has `0004_wild_legion` → ticket becomes `0005_…`).
- Update together: SQL filename, `meta/_journal.json` (`tag` = basename without `.sql`, unique `idx`), and `meta/NNNN_snapshot.json` (`prevId` = previous snapshot id).
- **Never** leave two `NNNN_*.sql` files with the same numeric prefix.
- **Never** keep both files and only “fix” the journal textually — that is not a resolution.
- **Never** invent a second `0001_*` that replaces main's `0001_*`.
- Prefer: take the ticket's schema SQL content → write it as the next free index → fix journal/snapshot. Do not line-merge migration journals when indexes collide.

Safety rules:
- Do not reset the branch.
- Do not auto-merge to main.
- Do not merge any other `ticket/T*` branch into this ticket (that pollutes history).
- Do not blindly choose ours/theirs without justification.
- Do not commit `node_modules/`, build caches, or `dist/` / `target/`.
- Preserve both ticket intent and latest main behavior when possible.

The ticket follows.
