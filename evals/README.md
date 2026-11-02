# jj skill evals

These evals check whether an agent using the `jujutsu` skill can get real
work done in a real jj repo. Each scenario becomes a
[Harbor](https://harborframework.com/docs) task: a container holding a
colocated jj repo, a plain-language request ("Rebase my feature bookmark
onto main"), and a check of the repo's end state. Only the end state is
graded. The commands the agent ran are recorded as diagnostics.

Harbor runs the agent, so any agent it supports works: `claude-code`,
`pi`, `codex`, `gemini-cli`, `opencode`, and about 30 more.

## Running

You need Docker and [uv](https://docs.astral.sh/uv/). Harbor itself runs
through `uvx`, pinned in `jj_eval/__main__.py`.

```bash
just eval-selftest 0.46.0     # oracle must pass and nop must fail every scenario; Docker only, no API calls
just eval 0.46.0              # Claude Code on every scenario against jj 0.46.0
just eval 0.46.0 --agent pi --model anthropic/claude-sonnet-5
just eval 0.46.0 --trials 3 --jobs 8 --scenario commit-large-file
just eval 0.46.0 --no-skill   # the same scenarios without the skill, as a baseline
just eval-report /tmp/jj-skill-eval/jobs/jj-0.37.0-claude-code /tmp/jj-skill-eval/jobs/jj-0.46.0-claude-code
```

Arguments after `--` go straight to `harbor run`, for example
`just eval 0.46.0 -- --ae MY_VAR=1`. `python -m jj_eval list` prints every
scenario and its prompt. `harbor view /tmp/jj-skill-eval/jobs` browses the
trials, including each agent's trajectory.

### Credentials

Agents run inside the containers, so they cannot use your keychain login.
Put credentials in `evals/.env`, which git ignores; `just eval` passes it to
Harbor with `--env-file`.

- **Claude Code on your subscription:** run `claude setup-token`, then add
  `CLAUDE_CODE_OAUTH_TOKEN=<token>` and `CLAUDE_FORCE_OAUTH=1`.
- **An API key:** add `ANTHROPIC_API_KEY=<key>`.
- **pi:** add the key for the model's provider, for example
  `ANTHROPIC_API_KEY` for `anthropic/...` models. `harbor agent auth pi`
  lists what it reads.

## How a run works

`just eval VERSION` writes one Harbor task per scenario to
`/tmp/jj-skill-eval/tasks/<run>/`. It then calls `harbor run` with
`--skill ../jujutsu`, which installs the skill where the chosen agent looks
for skills. Results land in `/tmp/jj-skill-eval/jobs/<run>/`, where `<run>`
is `jj-<version>-<agent>[-<model>]`. Both directories are wiped at the start
of a run.

Each task's image installs the official jj release binary for that version.
It then builds the starting repo with pinned seeds and timestamps, so the
commit and change IDs are identical on every build. Finally it deletes the
scenario code, so the agent cannot read the checks; Harbor copies the
checks in only after the agent finishes.

| Path in the container | What it is |
|---|---|
| `/app/repo` | The colocated jj repo the agent works in |
| `/app/origin.git` | A bare git remote, for the push and fetch scenarios |
| `/usr/local/bin/jj` | A shim that logs each jj call and its exit status, then runs the jj under test |
| `/usr/local/libexec/jj` | The jj under test, which the checks call directly |
| `/usr/local/bin/jj-eval-editor` | Stands in for `$EDITOR` and always fails, so an editor prompt errors instead of hanging |
| `/logs/agent/jj-invocations.log` | Every jj command the agent ran |

## Diagnostics

Each trial reports these metrics in its `reward.json`, and Harbor averages
them per job:

- **reward**: 1 if the end state is right, else 0.
- **jj_calls**: how many jj commands the agent ran.
- **failed_jj_calls**: jj commands that exited non-zero. A pass with failed
  calls means the agent recovered from a mistake, which is where most
  version drift shows, for example a flag removed between versions. Exit
  status 3 is not counted: it means a pipe such as `| head` closed early.
- **editor_prompts**: times jj or git tried to open an editor.

The trial's `verifier/check.json` holds the failure message and the failed
commands. `just eval-report` turns a job into a table, or lines up several
jobs side by side.

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

    def setup(self, sb):   # build the starting repo, at image build time
        stack(base_repo(sb), ("Add login page", {"src/login.txt": "login form\n"}))

    def check(self, sb):   # raise CheckFailure (via require) unless the end state is right
        bookmark = sb.repo.bookmark("feature-login")
        require(bookmark and bookmark.target == sb.repo.the("Add login page").commit_id, "...")

    def solve(self, sb):   # one reference solution, which Harbor's oracle agent runs
        sb.repo.jj("bookmark", "create", "feature-login", "-r", "@-")
```

Then run `just eval-selftest` for each jj version you care about. It
requires `check` to accept the state after `solve` (the oracle agent) and to
reject the untouched setup (the nop agent), so a scenario can be passed but
not by doing nothing. `uv run pytest` checks, without Docker, that no prompt
names a jj command.

Write checks that accept any reasonable route to the outcome. Find commits
by description (`repo.the("Add parser")`) rather than by change ID, because
the agent may rewrite them.
