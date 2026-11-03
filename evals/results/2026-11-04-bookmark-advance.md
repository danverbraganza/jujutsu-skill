# `jj bookmark advance` before pushing

Run on 2026-11-04 with Harbor 0.25.0, on jj 0.46.0 only, the latest release. The agent is Claude Code
2.1.316 with `claude-sonnet-5-5` and at most 40 turns, 3 trials per scenario.

- "Before" is the skill on `main`.
- "After" adds willjr's guidance to run `jj bookmark advance` before pushing, adjusted to advance to
  `@-` when the working copy is empty. A bare `jj bookmark advance` would put the bookmark on the empty
  commit, which jj refuses to push.

**Every scenario passes with both skills. On the new `push-new-commits` scenario, agents switch to the
documented command.**

| | Before | After |
|---|---|---|
| `push-new-commits` passed | 3/3 | 3/3 |
| How agents moved the bookmark there | `jj bookmark move feature --to @-` (3 of 3) | `jj bookmark advance --to @- feature` (3 of 3) |
| Failed jj calls in `push-new-commits` | 0 | 0 |
| The other 28 scenarios passed | 84/84 | 84/84 |
| Failed jj calls in the other 28 | 5 | 8 |

The new scenario's "before" trials ran alongside the "after" run. The other 28 scenarios' "before"
numbers come from the 2026-11-03 run in
[2026-11-03-skill-improvements.md](2026-11-03-skill-improvements.md), which used the same skill and the
same agent.

No agent advanced the bookmark onto the empty working-copy commit in either run, so the new warning
about that trap was never put to the test.

The 3 extra failed calls are in scenarios this change does not touch, and both kinds have shown up in
earlier runs:

- `edit-earlier-commit`: `jj new` or `jj edit` on the empty working-copy commit that jj had already
  abandoned (4 calls after, 2 before).
- `squash-into-parent`: `jj squash --from X --into Y` without `-m`, which opened the editor (1 call
  after, 0 before).

On 0.46, agents still try the removed `jj git push --allow-new` in `push-undescribed-change`, 3 times
before and 3 times after.
