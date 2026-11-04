# Non-colocated repos

Run on 2026-11-04 with Harbor 0.25.0, on jj 0.46.0 only, the latest release. The agent is Claude Code
2.1.316 with `claude-sonnet-5-5` and at most 40 turns, 3 trials per scenario, with the skill on `main`.

Scenario repos are no longer colocated with git, so git commands run in them fail with
`fatal: not a git repository`. The skill and the agent match the "after" run in
[2026-11-04-bookmark-advance.md](2026-11-04-bookmark-advance.md), which used colocated repos.

**Every scenario still passes. More than half of the agents start by running git, get the error, and
use jj from then on.**

| | Colocated (bookmark-advance run) | Not colocated |
|---|---|---|
| Passed | 87/87 | 87/87 |
| Failed jj calls | 8 | 5 |
| Trials whose first shell command ran git | not measured | 48/87 |
| Loaded the skill | not measured | 86/87 |
| Loaded the skill before the first shell command | not measured | 45/87 |

## Git attempts

Every git command was a read-only look at the repo, and all 48 came in the agent's first shell command,
usually next to `ls -a` or a check for `.jj`: `git log` 21 times, `git status` 18, `git rev-parse` 8,
`git reflog` 3, `git branch -a` 3, `git check-ignore` 2, and `git remote -v` once. No agent tried a git
command that changes anything. In 40 of the 48 trials the git command ran before the agent loaded the
skill. Each got `fatal: not a git repository`, carried on with jj, and passed.

One agent ran git again later: `git --git-dir=/app/origin.git branch` in `push-undescribed-change`, to
confirm its push. That works, because the bare remote at `/app/origin.git` is an ordinary git repo.

Trials are graded on the end state alone, so a git attempt does not fail a trial. The count is there to
grade on later.

## Failed jj calls

- `push-undescribed-change`: `jj git push -b quick-fix --allow-new` in all 3 trials. The flag was
  removed in 0.42; each agent then pushed without it.
- `edit-earlier-commit`: `jj new` on the empty working-copy commit that jj had already abandoned, in 2
  trials.

Both have shown up in earlier runs.
