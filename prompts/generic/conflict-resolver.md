# Generic Conflict Resolver Task

Read `conflict/context.md` in the run directory. It contains the full ticket context, plan, reviews, PR diff, conflicted files (with conflict markers), and the latest commits on main.

Your task:
1. Edit every conflicted file in-place to remove all conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`).
2. Resolve each conflict by preserving both the ticket intent and the latest main behavior where possible.
3. Do not blindly pick ours or theirs — reason through each conflict.
4. Write your output (stdout) as `conflict/resolution.md` summarising every conflict decision.

Safety rules:
- Do not reset the branch.
- Do not auto-merge to main.
- Do not blindly choose ours/theirs without justification.
- Preserve both ticket intent and latest main behavior when possible.

The ticket follows.
