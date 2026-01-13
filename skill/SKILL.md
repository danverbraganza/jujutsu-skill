---
name: jj-vcs
description: Guides agents through using the Jujutsu (jj) version control system. Activate when the user mentions jj, jujutsu, or when working in a repository with a .jj directory. Teaches proper workflow for atomic commits and change management.
---

# Jujutsu (jj) Version Control System

This skill helps you work with Jujutsu, a Git-compatible VCS with mutable commits and automatic rebasing.

**Tested with jj v0.37.0** - Commands may differ in other versions.

## Important: Automated/Agent Environment

When running as an agent, **always use `-m` flags** to provide messages inline rather than relying on editor prompts:

```bash
# Always use -m to avoid editor prompts
jj desc -m "message"      # NOT: jj desc
jj new -m "message"       # NOT: jj new (then describe separately)
jj squash -m "message"    # NOT: jj squash (which opens editor)
jj commit -m "message"    # NOT: jj commit
```

Editor-based commands will fail in non-interactive environments.

## Core Concepts

### The Working Copy is a Commit

In jj, your working directory is always a commit (referenced as `@`). Changes are automatically snapshotted when you run any jj command. There is no staging area.

### Commits Are Mutable

**CRITICAL**: Unlike git, jj commits can be freely modified. This enables a high-quality commit workflow:

1. Create a commit with your intended message first
2. Make your changes
3. The commit automatically captures your work
4. Refine the commit using `squash`, `split`, or `absorb` as needed

### Change IDs vs Commit IDs

- **Change ID**: A stable identifier (like `tqpwlqmp`) that persists when a commit is rewritten
- **Commit ID**: A content hash (like `3ccf7581`) that changes when commit content changes

Prefer using Change IDs when referencing commits in commands.

## Essential Workflow

### Starting Work: Describe First, Then Code

**Always create your commit message before writing code:**

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
"Verb object" - exactly one sentence, no period

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

# View diff of working copy
jj diff
```

### Moving Between Commits

```bash
# Create a new empty commit on top of current
jj new

# Create new commit with message
jj new -m "Commit message"

# Edit an existing commit (working copy becomes that commit)
jj edit <change-id>
```

## Refining Commits

### Squashing Changes

Move changes from current commit into its parent:

```bash
# Squash all changes into parent
jj squash

# Squash interactively (choose what to move)
jj squash -i
```

### Splitting Commits

Divide a commit that does too much:

```bash
# Split current commit interactively
jj split

# Split a specific commit
jj split -r <change-id>
```

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

## Working with Bookmarks (Branches)

Bookmarks are jj's equivalent to git branches:

```bash
# Create a bookmark at current commit
jj bookmark create my-feature

# Move bookmark to a different commit
jj bookmark move my-feature -r <change-id>

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

### Pushing Changes (Mirrored Repository Context)

**NOTE**: You are likely working on a mirrored clone of the repository, not the original. This mirror has its own remote configured.

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

jj allows committing conflicts - you can resolve them later:

```bash
# View conflicts
jj st

# Resolve conflicts with external tool
jj resolve

# Continue working despite conflicts - jj allows this
```

## Preserving Commit Quality

**IMPORTANT**: Because commits are mutable, always refine them:

1. **Review your commit**: `jj show @` or `jj diff`
2. **Is it atomic?** One logical change per commit
3. **Is the message clear?** "Verb object" format, one sentence
4. **Are there unrelated changes?** Use `jj split` to separate them
5. **Should changes be elsewhere?** Use `jj squash` or `jj absorb`

## Quick Reference

| Action | Command |
|--------|---------|
| Describe commit | `jj desc -m "message"` |
| View status | `jj st` |
| View log | `jj log` |
| View diff | `jj diff` |
| New commit | `jj new -m "message"` |
| Edit commit | `jj edit <id>` |
| Squash to parent | `jj squash` |
| Split commit | `jj split` |
| Auto-distribute | `jj absorb` |
| Abandon commit | `jj abandon <id>` |
| Create bookmark | `jj bookmark create <name>` |
| Push bookmark | `jj git push -b <name>` |

## Best Practices Summary

1. **Describe first**: Set the commit message before coding
2. **One change per commit**: Keep commits atomic and focused
3. **Use change IDs**: They're stable across rewrites
4. **Refine commits**: Leverage mutability for clean history
5. **Embrace the workflow**: No staging area, no stashing - just commits
