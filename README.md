# jj VCS Agent Skill

An Agent Skill that helps AI coding agents work with the Jujutsu (jj) version control system.

## Overview

This repository provides an Agent Skill for Claude Code and other compatible AI agents to effectively use the Jujutsu VCS. The skill teaches agents the proper workflow and commands for creating atomic, well-documented commits using jj.

## Compatibility

**Tested with:** jj v0.37.0

This skill is designed for jj v0.37.0 and may work with other versions, though compatibility is not guaranteed.

## What is Jujutsu?

Jujutsu (jj) is a Git-compatible version control system that offers several advantages:

- **Working copy as a commit**: The working directory is always a commit, automatically snapshotting changes
- **No staging area**: Changes are moved directly between commits using `squash` and `split`
- **Automatic rebasing**: Descendant commits are automatically rebased when parent commits change
- **Mutable commits**: Commits can be freely edited, split, and squashed
- **Change IDs**: Stable identifiers that persist across commit rewrites
- **Conflict handling**: Conflicts can be committed and resolved later

## Installation

Copy the `skill/` directory into your project's `.claude/skills/` directory:

```bash
cp -r skill/ /path/to/your/project/.claude/skills/jj-vcs/
```

Or install it as a global skill:

```bash
cp -r skill/ ~/.claude/skills/jj-vcs/
```

## Skill Contents

```
skill/
└── SKILL.md    # Main skill file with jj workflow instructions
```

## Key Workflow Philosophy

The skill emphasizes:

1. **Describe-first commits**: Use `jj desc -m "message"` before making changes
2. **Atomic commits**: Each commit should represent one logical change
3. **Commit quality preservation**: Leverage jj's mutability to refine commits
4. **Clean history**: Use `squash`, `split`, and `absorb` to maintain a readable history

## Contributing

Contributions are welcome. Please ensure any changes are compatible with jj v0.37.0.

## License

MIT
