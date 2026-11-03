# Committing a subset of files

Run on 2026-11-04 with Harbor 0.25.0, on jj 0.46.0 only, the latest release. The agent is Claude Code
2.1.316 with `claude-sonnet-5-5` and at most 40 turns, 3 trials per scenario.

- "Before" is the skill on `main`.
- "After" adds atimofeev's subset-commit guidance. `jj commit -m <message> <paths>` commits only those
  paths and leaves the rest in the working copy, and `jj restore <paths>` discards changes rather than
  moving them.

**Every scenario passes with both skills. The new `commit-some-files` scenario mostly measured agents
committing with plain git, not the new guidance.**

| | Before | After |
|---|---|---|
| `commit-some-files` passed | 3/3 | 3/3 |
| How agents committed there | `git add` and `git commit`, before loading the skill (3 of 3) | `git add` and `git commit` (2 of 3); `jj commit -m "Add API endpoint" src/api.txt` after loading the skill (1 of 3) |
| The other 28 scenarios passed | 84/84 | 84/84 |
| Failed jj calls in the other 28 | 5 | 6 |

The new scenario's "before" trials ran alongside the "after" run. The other 28 scenarios' "before"
numbers come from the 2026-11-03 run in
[2026-11-03-skill-improvements.md](2026-11-03-skill-improvements.md), which used the same skill and the
same agent.

## Agents reach for git

In a colocated repo, `git add src/api.txt && git commit` leaves an end state the check accepts. jj
imports the git commit, and the unrelated edit stays in an undescribed `@`. So the scenario passes
whether or not the agent knows `jj commit <paths>`.

The same happens in other scenarios, also without failing any. Agents ran mutating git commands in 6
of 84 trials of the 28 shared scenarios before, and in 9 of 84 after:

- `git tag` in `tag-release`
- `git checkout -- <paths>` or `git restore` in `discard-awkward-paths`
- `git add` and `git commit` in `commit-large-file`
- `git revert` in `revert-commit`

About half the trials loaded the skill before their first shell command: 49 of 84 before, and 44 of 87
after.

## Failed jj calls

The one extra failed call is in a scenario this change does not touch: `jj new` on the empty
working-copy commit that jj already abandoned, in `edit-earlier-commit` (3 calls after, 2 before). On
0.46, agents still try the removed `jj git push --allow-new` in `push-undescribed-change`, 3 times before
and 3 times after.
