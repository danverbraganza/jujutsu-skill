# Skill improvements for jj 0.46

Run on 2026-11-03 with Harbor 0.25.0, alongside the baseline in
[2026-11-03-jj-0.37.0-vs-0.46.0.md](2026-11-03-jj-0.37.0-vs-0.46.0.md) and with the same agent:
Claude Code 2.1.316, `claude-sonnet-5-5`, at most 40 turns, 28 scenarios × 3 trials per jj version.
"Before" is the skill as of `b066831`. "After" adds:

- `jj revert -r <id> -B @`, noting that `jj backout` no longer exists.
- Quoting paths that contain fileset syntax as `'file:"..."'`, with a warning that a leading `~` means
  "everything except".
- `jj op restore <operation-id>`, noting that `jj undo` takes no operation ID.
- `jj split -m <message> <paths>` as a non-interactive split. The skill used to say `jj split` always
  hangs.
- `-o`/`--onto` in the rebase examples instead of the deprecated `-d`.

**Every scenario still passes on both versions, and failed jj calls fell from 8 to 5 on 0.37 and from
10 to 5 on 0.46.**

| | 0.37.0 before | 0.37.0 after | 0.46.0 before | 0.46.0 after |
|---|---|---|---|---|
| Passed | 84/84 | 84/84 | 84/84 | 84/84 |
| jj calls that exited non-zero | 8 | 5 | 10 | 5 |
| Paths that failed to parse as filesets | 2 | 0 | 2 | 0 |
| `jj revert` given an unsupported `-m` | 1 | 0 | 2 | 0 |
| jj calls | 382 | 374 | 387 | 375 |
| Editor prompts | 0 | 0 | 0 | 0 |
| Agent cost, as Harbor reports it | $2.77 | $3.22 | $3.22 | $3.04 |

## What the changes did not move

- No agent tried `jj backout`, before or after, so this run does not test that note. Agents in an
  earlier run, with the first version of the harness and Claude Code 2.1.205, did try it.
- On 0.37, `jj git push -b` still fails for a new bookmark until it is tracked (3 calls before and
  after). The skill now targets 0.46, where it does not.
- On 0.46, agents still try `jj git push --allow-new`, which jj removed in 0.42 (3 calls before and
  after). The skill could say outright that the flag is gone, and that `jj git push -b` tracks a new
  bookmark itself.
- `jj new` or `jj edit` on the empty working-copy commit that jj already abandoned (2 or 3 calls per
  run, before and after).

## jj 0.46.0, before and after

| Scenario | before | after |
|---|---|---|
| abandon-middle-commit | 3/3 pass | 3/3 pass |
| absorb-fixups | 3/3 pass | 3/3 pass |
| add-workspace | 3/3 pass | 3/3 pass |
| commit-large-file | 3/3 pass | 3/3 pass |
| commit-working-copy | 3/3 pass | 3/3 pass |
| create-bookmark | 3/3 pass | 3/3 pass |
| discard-awkward-paths | 3/3 pass (2 failed jj calls) | 3/3 pass |
| edit-earlier-commit | 3/3 pass (3 failed jj calls) | 3/3 pass (2 failed jj calls) |
| fetch-and-rebase | 3/3 pass | 3/3 pass |
| forget-colleague-bookmark | 3/3 pass | 3/3 pass |
| merge-two-bookmarks | 3/3 pass | 3/3 pass |
| move-bookmark-forward | 3/3 pass | 3/3 pass |
| push-new-bookmark | 3/3 pass | 3/3 pass |
| push-undescribed-change | 3/3 pass (3 failed jj calls) | 3/3 pass (3 failed jj calls) |
| rebase-tree-onto-main | 3/3 pass | 3/3 pass |
| recover-abandoned-commit | 3/3 pass | 3/3 pass |
| reorder-commits | 3/3 pass | 3/3 pass |
| resolve-rebase-conflict | 3/3 pass | 3/3 pass |
| restore-file-from-old-commit | 3/3 pass | 3/3 pass |
| revert-commit | 3/3 pass (2 failed jj calls) | 3/3 pass |
| reword-older-commit | 3/3 pass | 3/3 pass |
| set-commit-author | 3/3 pass | 3/3 pass |
| split-by-path | 3/3 pass | 3/3 pass |
| squash-file-into-ancestor | 3/3 pass | 3/3 pass |
| squash-into-parent | 3/3 pass | 3/3 pass |
| start-change-on-main | 3/3 pass | 3/3 pass |
| stop-tracking-secret | 3/3 pass | 3/3 pass |
| tag-release | 3/3 pass | 3/3 pass |
| **passed** | 84/84 | 84/84 |

## jj 0.37.0, before and after

| Scenario | before | after |
|---|---|---|
| abandon-middle-commit | 3/3 pass | 3/3 pass |
| absorb-fixups | 3/3 pass | 3/3 pass |
| add-workspace | 3/3 pass | 3/3 pass |
| commit-large-file | 3/3 pass | 3/3 pass |
| commit-working-copy | 3/3 pass | 3/3 pass |
| create-bookmark | 3/3 pass | 3/3 pass |
| discard-awkward-paths | 3/3 pass (2 failed jj calls) | 3/3 pass |
| edit-earlier-commit | 3/3 pass (2 failed jj calls) | 3/3 pass (2 failed jj calls) |
| fetch-and-rebase | 3/3 pass | 3/3 pass |
| forget-colleague-bookmark | 3/3 pass | 3/3 pass |
| merge-two-bookmarks | 3/3 pass | 3/3 pass |
| move-bookmark-forward | 3/3 pass | 3/3 pass |
| push-new-bookmark | 3/3 pass (3 failed jj calls) | 3/3 pass (3 failed jj calls) |
| push-undescribed-change | 3/3 pass | 3/3 pass |
| rebase-tree-onto-main | 3/3 pass | 3/3 pass |
| recover-abandoned-commit | 3/3 pass | 3/3 pass |
| reorder-commits | 3/3 pass | 3/3 pass |
| resolve-rebase-conflict | 3/3 pass | 3/3 pass |
| restore-file-from-old-commit | 3/3 pass | 3/3 pass |
| revert-commit | 3/3 pass (1 failed jj call) | 3/3 pass |
| reword-older-commit | 3/3 pass | 3/3 pass |
| set-commit-author | 3/3 pass | 3/3 pass |
| split-by-path | 3/3 pass | 3/3 pass |
| squash-file-into-ancestor | 3/3 pass | 3/3 pass |
| squash-into-parent | 3/3 pass | 3/3 pass |
| start-change-on-main | 3/3 pass | 3/3 pass |
| stop-tracking-secret | 3/3 pass | 3/3 pass |
| tag-release | 3/3 pass | 3/3 pass |
| **passed** | 84/84 | 84/84 |
