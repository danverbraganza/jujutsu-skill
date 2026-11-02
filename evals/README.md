# jj skill evals

These evals check whether an agent using the `jujutsu` skill can get real
work done in a real jj repo. Each scenario builds a colocated jj repo, asks
Claude Code for an outcome in plain language ("Rebase my feature bookmark
onto main"), and then inspects the repo. Only the end state is graded. The
commands the agent ran do not affect pass or fail; they are recorded as
diagnostics.

## Running

```bash
just eval-selftest                          # validate every scenario on jj 0.37.0 and 0.46.0; no agent, no API calls
just eval 0.46.0                            # run all scenarios with Claude Code against jj 0.46.0
just eval 0.46.0 --model opus --jobs 8      # any `python -m jj_eval run` flag works
just eval 0.46.0 --scenario commit-large-file --trials 3
just eval-compare /tmp/jj-skill-eval/jj-0.37.0-sonnet /tmp/jj-skill-eval/jj-0.46.0-sonnet
just eval 0.46.0 --work-dir /tmp/jj-skill-eval/after    # after editing the skill, keeping the old run
just eval-compare /tmp/jj-skill-eval/jj-0.46.0-sonnet /tmp/jj-skill-eval/after/jj-0.46.0-sonnet
```

`just eval` downloads the official jj release binary for that version into
`~/.cache/jj-skill-eval/` (override with `JJ_EVAL_CACHE`), or tests a
binary you name with `--jj PATH`. `--no-skill` runs the same scenarios
without the skill, as a baseline. `python -m jj_eval list` prints every
scenario and its prompt.

The self-test downloads jj 0.37.0 and 0.46.0 by default. Set
`JJ_EVAL_VERSIONS=0.46.0,0.47.0` to test other versions.

## What a run looks like

Each run lives at a fixed path,
`/tmp/jj-skill-eval/jj-<version>-<model>/<scenario>/trial-<n>/`, and is wiped
at the start of the run:

| Path | What it is |
|---|---|
| `repo/` | The colocated jj repo the agent works in (its cwd) |
| `origin.git/` | A bare git remote, for the push and fetch scenarios |
| `bin/jj` | A shim that logs each jj call and its exit status, then runs the jj under test |
| `bin/jj-eval-editor` | Stands in for `$EDITOR` and always fails, so an editor prompt errors immediately instead of hanging |
| `jj-config.toml`, `gitconfig` | The only jj and git config in effect; your own config is ignored |
| `plugin/` | The skill under test, loaded with `claude --plugin-dir` |
| `transcript.jsonl` | Claude Code's `stream-json` output |
| `jj-invocations.log` | Every jj command the agent ran, with its exit status |
| `result.json` | The check outcome plus diagnostics |

The run directory also gets `summary.md` and `results.json`.

The agent runs `claude -p` with `--setting-sources project,local`,
`--strict-mcp-config`, and auto-memory disabled. That keeps your
`~/.claude/CLAUDE.md`, user skills, hooks, plugins, and MCP servers out of the
run, so the skill in this repo is the only jj guidance the agent gets.
Permissions are bypassed inside the sandbox.

Setup is deterministic. Setup commands run with a pinned randomness seed
and pinned timestamps, so a scenario's starting commit and change IDs are
identical on every run of a given jj version.

## Diagnostics

`summary.md` reports these per scenario, beyond pass or fail:

- **Skill used**: whether the agent loaded the jujutsu skill.
- **Failed jj calls**: jj commands that exited non-zero. A pass with failed
  calls means the agent recovered from a mistake. This column shows most
  version drift, for example a flag that was removed between versions.
- **Warnings**: the distinct `Warning:` lines jj printed, such as
  deprecations and refused snapshots.
- **Editor prompts**: times jj or git tried to open an editor.
- **Raw git commands**: shell commands that invoked `git` directly instead of jj.

## Scenarios

| Scenario | Exercises |
|---|---|
| `commit-working-copy` | `jj commit`, or describe then new |
| `reword-older-commit` | `jj describe -r` on a commit that has descendants |
| `start-change-on-main` | `jj new main`, `jj bookmark create`, leaving in-progress work alone |
| `create-bookmark` | `jj bookmark create -r` on a commit other than `@` |
| `move-bookmark-forward` | `jj bookmark move --to`, not onto the empty working-copy commit |
| `edit-earlier-commit` | `jj edit` or `jj new` plus `jj squash` into an ancestor, with automatic rebasing of descendants |
| `restore-file-from-old-commit` | `jj restore --from` |
| `abandon-middle-commit` | `jj abandon` with descendants |
| `recover-abandoned-commit` | `jj undo` or `jj op restore` |
| `rebase-tree-onto-main` | `jj rebase -s` or `-b` for a commit with two child branches |
| `squash-into-parent` | `jj squash` when both commits have descriptions (the default opens an editor) |
| `squash-file-into-ancestor` | `jj squash --into` with paths |
| `absorb-fixups` | `jj absorb` |
| `split-by-path` | `jj split` with paths and `-m` |
| `reorder-commits` | `jj rebase -r` with `--insert-before` or `--insert-after` |
| `revert-commit` | `jj revert`, which replaced `jj backout` |
| `merge-two-bookmarks` | `jj new A B` |
| `set-commit-author` | `jj metaedit --author`; `jj describe --author` was removed in 0.42 |
| `push-new-bookmark` | Pushing a never-pushed bookmark; 0.37 requires `jj bookmark track` first |
| `push-undescribed-change` | jj refuses to push a commit with no description |
| `fetch-and-rebase` | `jj git fetch`, then rebase onto the updated main |
| `forget-colleague-bookmark` | `jj bookmark forget` rather than `delete`; delete would remove the branch from origin on the next push |
| `commit-large-file` | A 3 MB file, over the default 1 MiB `snapshot.max-new-file-size` |
| `resolve-rebase-conflict` | Rebase conflict resolved by editing jj's conflict markers |
| `discard-awkward-paths` | `jj restore` on `notes (draft).md` and `~scratch.txt`; unquoted, jj parses these as fileset syntax and `~` means "everything except" |
| `stop-tracking-secret` | `jj file untrack` only works once the file is ignored |
| `add-workspace` | `jj workspace add -r`; on 0.46 this also creates a git worktree |
| `tag-release` | `jj tag set` |

Sources: the commands in Danver Braganza's
[most frequently used jj commands](https://danverbraganza.com/writings/most-frequent-jj-commands),
Steve Klabnik's [Jujutsu tutorial](https://steveklabnik.github.io/jujutsu-tutorial/),
the [jj CLI reference](https://jj-vcs.github.io/jj/latest/cli-reference/), and
the breaking changes between 0.37 and 0.46 in the
[jj changelog](https://github.com/jj-vcs/jj/blob/main/CHANGELOG.md).

## Adding a scenario

Subclass `Scenario` in one of the modules under `jj_eval/scenarios/`:

```python
class CreateBookmark(Scenario):
    name = "create-bookmark"
    tags = ("everyday",)
    prompt = "Create a bookmark called feature-login on the commit that adds the login page."

    def setup(self, sb):   # build the starting repo
        stack(base_repo(sb), ("Add login page", {"src/login.txt": "login form\n"}))

    def check(self, sb):   # raise CheckFailure (via require) unless the end state is right
        bookmark = sb.repo.bookmark("feature-login")
        require(bookmark and bookmark.target == sb.repo.the("Add login page").commit_id, "...")

    def solve(self, sb):   # one reference solution; only the self-test runs it
        sb.repo.jj("bookmark", "create", "feature-login", "-r", "@-")
```

`just eval-selftest` enforces three rules on every scenario, on every jj
version:

1. `check` fails on the untouched setup, so the scenario cannot pass by doing nothing.
2. `check` passes after `solve`, so it can be passed.
3. The prompt never names a jj command.

Write checks that accept any reasonable route to the outcome. Find commits
by description (`repo.the("Add parser")`) rather than by change ID, because
the agent may rewrite them.
