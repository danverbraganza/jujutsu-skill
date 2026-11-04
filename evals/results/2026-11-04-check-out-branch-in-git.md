# Checking out a branch in git, in a colocated repo

Run on 2026-11-04 with Harbor 0.25.0, on jj 0.46.0 only, the latest release. The agent is Claude Code
2.1.316 with `claude-sonnet-5-5` and at most 40 turns, 3 trials, with the skill on `main`.

`check-out-branch-in-git` is the first scenario that opts in to a colocated repo. A git-only release
script needs `release` checked out in git with a clean working tree, and the user has uncommitted work
in jj.

**All 3 trials pass, and no jj call failed. Every agent loaded the skill first, gave the work a
description, and checked out release with git.**

| Trials | Route |
|---|---|
| 2 | `jj desc -m "WIP: ..."`, then `jj new release`, then `git checkout release` to put git on the branch |
| 1 | `jj desc -m "WIP: ..."` and a bookmark on it, then a bare `git checkout release`, which carried the work over as uncommitted changes. `jj restore` then dropped that copy, leaving the work in the described commit |

The self-test passes on jj 0.46.0 and 0.37.0. The reference solution, `jj new` and then
`git checkout release`, passes. An untouched repo fails, because git's HEAD is detached. A bare
`git checkout release` alone fails, because git's working tree is left dirty.
