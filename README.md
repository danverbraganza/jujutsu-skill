# jj VCS Agent Skill

An Agent Skill that helps AI coding agents work with the Jujutsu (jj) version control system.

## Overview

This repository provides an Agent Skill for Claude Code and other compatible AI agents to effectively use the Jujutsu VCS. The skill teaches agents the proper workflow and commands for creating atomic, well-documented commits using jj.

## Compatibility

**Tested with:** jj v0.46.0

This skill is designed for jj v0.46.0 and may work with other versions, though compatibility is not guaranteed. The [latest eval run](evals/results/2026-11-03-skill-improvements.md) passes on both v0.37.0 and v0.46.0.

## What is Jujutsu?

Jujutsu (jj) is a Git-compatible version control system that offers several advantages:

- **Working copy as a commit**: The working directory is always a commit, automatically snapshotting changes
- **No staging area**: Changes are moved directly between commits using `squash` and `split`
- **Automatic rebasing**: Descendant commits are automatically rebased when parent commits change
- **Mutable commits**: Commits can be freely edited, split, and squashed
- **Change IDs**: Stable identifiers that persist across commit rewrites
- **Conflict handling**: Conflicts can be committed and resolved later

## Installation

If you use [just](just.systems), you can run:

```
just install
```

Copy the `jujutsu/` directory into your project's `.claude/skills/` directory:

```bash
cp -r jujutsu/ /path/to/your/project/.claude/skills/jujutsu/
```

Or install it as a global skill:

```bash
cp -r jujutsu/ ~/.claude/skills/jujutsu/
```

## Skill Contents

```
jujutsu/
└── SKILL.md    # Main skill file with jj workflow instructions
```

## Key Workflow Philosophy

The skill emphasizes:

1. **Describe-first commits**: Use `jj desc -m "message"` before making changes
2. **Atomic commits**: Each commit should represent one logical change
3. **Commit quality preservation**: Leverage jj's mutability to refine commits
4. **Clean history**: Use `squash`, `split`, and `absorb` to maintain a readable history

## Evaluation

In an end-to-end evaluation with [Harbor](https://harborframework.com/docs), the skill lets Claude Code
complete 36% more tasks than it does without the skill: 100% of trials succeed with it (90 of 90), and
73% without it (66 of 90). Both runs used the same 30 scenarios, three trials each, against jj 0.46.0.

Each scenario gives the agent a plain-language request, such as "Rebase my feature bookmark onto main",
in a real jj repo, and grades only the repo's end state. Most scenarios use a jj repo that is not
colocated with git, so git commands fail and the agent has to use jj. Scenarios about using jj and git
together run in a colocated repo. Only Claude Code has been tested so far, with `claude-sonnet-5-5`.

### Running the evals

`evals/` holds the scenarios and the harness. Each scenario runs in a container with an official jj
release. Any agent Harbor supports works, including Claude Code and pi.

```bash
just eval-selftest 0.46.0              # check every scenario with Harbor's oracle and nop agents, no API calls
just eval 0.46.0                       # run Claude Code on the scenarios against jj 0.46.0
just eval 0.46.0 --agent pi --model anthropic/claude-sonnet-5
just eval 0.46.0 --no-skill            # the same scenarios without the skill, for comparison
```

See [evals/README.md](evals/README.md) for credentials, the scenarios, and the diagnostics.

## Contributing

Contributions are welcome. Please ensure any changes are compatible with jj v0.46.0; `just eval 0.46.0` checks this.

## License

MIT
