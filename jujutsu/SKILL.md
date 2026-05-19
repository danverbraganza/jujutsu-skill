---
name: jujutsu
description: "**REQUIRED** - Always activate FIRST on any git/VCS operations (commit, status, branch, push, etc.), especially when HEAD is detached. If `.jj/` exists -> this is a Jujutsu (jj) repo - raw git commands can corrupt data. Essential git safety instructions inside. DO NOT IGNORE."
allowed-tools: Bash(jj *), Read
---

# Jujutsu (jj) Version Control System

This skill helps you work with Jujutsu, a Git-compatible VCS with mutable commits and automatic rebasing.

**Tested with jj v0.37.0** - Commands may differ in other versions.

## Important: Automated/Agent Environment

When running as an agent:

1. **Always use `-m` flags** to provide messages inline rather than relying on editor prompts:

```bash
# Always use -m to avoid editor prompts
jj desc -m "message"      # NOT: jj desc
jj squash -m "message"    # NOT: jj squash (which opens editor)
```

Editor-based commands will fail in non-interactive environments.

2. **Always append the attribution footer** when setting a commit message. Before calling `jj desc -m` or `jj new -m`, read `.claude/settings.json` and extract `attribution.commit`. Append it literally to the message:

```bash
# Example: if attribution.commit is "\n\nAI-Assisted: Claude Code, Anthropic Models"
jj desc -m "Add login endpoint

AI-Assisted: Claude Code, Anthropic Models"
```

If `.claude/settings.json` does not exist or has no `attribution.commit` field, omit the footer.

3. **Verify operations with `jj st`** after mutations (`squash`, `abandon`, `rebase`, `restore`) to confirm the operation succeeded.

## Core Concepts

### The Working Copy is a Commit

In jj, your working directory is always a commit (referenced as `@`). Changes are automatically snapshotted when you run any jj command. There is no staging area.

There is no need to run `jj commit`.

### Commits Are Mutable

**CRITICAL**: Unlike git, jj commits can be freely modified after creation. You can update descriptions, squash changes, rebase, and absorb — all without creating new commits. See "Essential Workflow" below for the recommended working pattern.

### Change IDs vs Commit IDs

- **Change ID**: A stable identifier (like `tqpwlqmp`) that persists when a commit is rewritten — prefer these when referencing commits
- **Commit ID**: A content hash (like `3ccf7581`) that changes when commit content changes

### Revsets

jj uses a revset language to select commits in commands. Common revsets:

- `@` — the working copy commit
- `@-` — the parent of the working copy
- `::@` — all ancestors of `@`
- `@::` — all descendants of `@`
- `trunk()..@` — commits between trunk and `@` (your branch)
- `bookmarks()` — all commits with bookmarks

Use revsets with `-r` flags: `jj log -r 'trunk()..@'`

## Essential Workflow

### Starting Work: Describe First, Then Code

**Always create your commit message before writing code:**

Validate that you're on a blank revision with `jj st`. If you are not, you should type:

```bash
jj new
```

```bash
# First, describe what you intend to do
jj desc -m "Add user authentication to login endpoint"

# Then make your changes - they automatically become part of this commit
# ... edit files ...

# Check status
jj st
```

### Creating Atomic Commits

Each commit should represent ONE logical change. Use this format for commit messages:

```
Examples:
- "Add validation to user input forms"
- "Fix null pointer in payment processor"
- "Remove deprecated API endpoints"
- "Update dependencies to latest versions"
```

### Viewing History

```bash
# View recent commits
jj log

# View with patches
jj log -p

# View specific commit
jj show <change-id>

# View diff of working copy (use --git for familiar +/- format)
jj diff --git
```

**IMPORTANT: `jj diff` output format**: The default `jj diff` output uses a side-by-side line number format (e.g. `26   26:`) that looks very different from git's `+`/`-` prefix format. This is **normal and correct** — it is NOT corrupted or showing stale content. However, to avoid confusion, **always use `jj diff --git`** to get standard unified diff format with `+`/`-` lines.

### Moving Between Commits

```bash
# Create a new empty commit on top of current
jj new

# Create new commit with message
jj new -m "Commit message"

# Edit an existing commit (working copy becomes that commit)
jj edit <change-id>

# Edit the previous commit
jj prev -e

# Edit the next commit
jj next -e
```

## Refining Commits

### Squashing Changes

Move changes from current commit into its parent:

```bash
# Squash all changes into parent
jj squash
```

**Note**: `jj squash -i` opens an interactive UI and will hang in agent environments. Avoid it.

### Splitting Commits

**Warning**: `jj split` is interactive and will hang in agent environments. To divide a commit, use `jj restore` to move changes out, then create separate commits manually.

### Absorbing Changes

Automatically distribute changes to the commits that last modified those lines:

```bash
# Absorb working copy changes into appropriate ancestor commits
jj absorb
```

### Abandoning Commits

Remove a commit entirely (descendants are rebased to its parent):

```bash
jj abandon <change-id>
```

### Undoing Operations

Reverse the last jj operation:

```bash
jj undo
```

This reverts the repository to its state before the previous command. Useful for recovering from mistakes like accidental `abandon`, `squash`, or `rebase`.

### Rebasing Commits

Move commits to a different parent:

```bash
# Rebase current branch onto a destination
jj rebase -d <destination>

# Rebase a specific revision (without descendants) onto a destination
jj rebase -r <change-id> -d <destination>

# Rebase a revision and all its descendants
jj rebase -s <change-id> -d <destination>

# Rebase onto trunk (common: update your branch to latest main)
jj rebase -d main
```

### Restoring Files

Discard changes to specific files or restore files from another revision:

```bash
# Discard all uncommitted changes in working copy (restore from parent)
jj restore

# Discard changes to specific files
jj restore path/to/file.txt

# Restore files from a specific revision
jj restore --from <change-id> path/to/file.txt
```

## Working with Bookmarks (Branches)

Bookmarks are jj's equivalent to git branches:

```bash
# Create a bookmark at current commit
jj bookmark create my-feature -r@

# Move bookmark to a different commit
jj bookmark move my-feature --to <change-id>

# List bookmarks
jj bookmark list

# Delete a bookmark
jj bookmark delete my-feature
```

## Git Integration

### Working with Existing Git Repos

```bash
# Clone a git repository
jj git clone <url>

# Initialize jj in an existing git repo
jj git init --colocate
```

### Fetching Remote Changes

```bash
# Fetch all branches from the default remote
jj git fetch

# Fetch from a specific remote
jj git fetch --remote <remote-name>

# Fetch specific branches
jj git fetch -b <branch-name>
```

After fetching, rebase your work onto the updated trunk: `jj rebase -d main`

### Switching Between jj and git (Colocated Repos Only)

**This section only applies to colocated repos** (where both `.jj/` and `.git/` exist). In non-colocated repos, do not use git commands — they will corrupt jj state.

In a colocated repository, you can use both jj and git commands with care:

**Switching to git mode** (e.g., for merge workflows):
```bash
# First, ensure your jj working copy is clean
jj st

# Then checkout a branch with git
git checkout <branch-name>
```

**Switching back to jj mode**:
```bash
# Use jj edit to resume working with jj
jj edit <change-id>
```

**Important notes:**
- Git may complain about uncommitted changes if jj's working copy differs from the git HEAD
- ALWAYS ensure your work is committed in jj before switching to git
- After git operations, jj will detect and incorporate the changes on next command

### Pushing Changes

When the user asks you to push changes:

```bash
# Push a specific bookmark to the remote
jj git push -b <bookmark-name>

# Example: push the main bookmark
jj git push -b main
```

**Before pushing, ensure:**
1. Your bookmark points to the correct commit (bookmarks don't auto-advance like git branches)
2. The commits are refined and atomic
3. The user has explicitly requested the push

**IMPORTANT**: Unlike git branches, jj bookmarks do not automatically move when you create new commits. You must manually update them before pushing:

```bash
# Move an existing bookmark to the current commit
jj bookmark move my-feature --to @

# Then push it
jj git push -b my-feature
```

If no bookmark exists for your changes, create one first:

```bash
# Create a bookmark at the current commit
jj bookmark create my-feature

# Then push it
jj git push -b my-feature
```

## Handling Conflicts

jj allows committing conflicts — you can resolve them later:

```bash
# View conflicts
jj st
```

**Agent conflict resolution**: Do not use `jj resolve` (interactive). Instead, edit the conflicted files directly to remove conflict markers, then run `jj st` to verify resolution.

## Preserving Commit Quality

**IMPORTANT**: Because commits are mutable, always refine them before considering work done:

1. **Review your commit**: `jj show @` or `jj diff --git`
2. **Is it atomic?** One logical change per commit
3. **Is the message clear?** Use imperative verb phrase in sentence case format with no full stop: e.g. "Add login endpoint", "Fix null pointer in payment processor", "Remove deprecated API endpoints"
4. **Are there unrelated changes?** Use `jj restore` to move changes out, then create separate commits
5. **Should changes be elsewhere?** Use `jj squash` or `jj absorb`

## Quick Reference

| Action | Command |
|--------|---------|
| Describe commit | `jj desc -m "message"` |
| View status | `jj st` |
| View log | `jj log` |
| View diff | `jj diff --git` |
| New commit | `jj new -m "message"` (use `jj st` first; skip if `@` is empty) |
| Edit commit | `jj edit <id>` |
| Squash to parent | `jj squash` |
| Auto-distribute | `jj absorb` |
| Rebase | `jj rebase -d <destination>` |
| Abandon commit | `jj abandon <id>` |
| Undo last operation | `jj undo` |
| Restore files | `jj restore [paths]` |
| Create bookmark | `jj bookmark create <name>` |
| Fetch remote | `jj git fetch` |
| Push bookmark | `jj git push -b <name>` |

## Best Practices Summary

1. **Describe first**: Set the commit message before coding
2. **One change per commit**: Keep commits atomic and focused
3. **Use change IDs**: They're stable across rewrites
4. **Refine commits**: Leverage mutability for clean history
5. **Embrace the workflow**: No staging area, no stashing - just commits
