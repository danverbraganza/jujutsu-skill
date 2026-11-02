"""A disposable directory holding one scenario run: the repo, its remote, and the agent's tooling.

Layout under `root`:
    repo/                    the colocated jj repo the agent works in (cwd)
    origin.git/              bare git remote, for scenarios that push or fetch
    bin/jj                   shim that logs each agent jj call, then runs the jj under test
    bin/jj-eval-editor       stand-in editor that always fails, so editor prompts error fast
    jj-config.toml           JJ_CONFIG for every jj call (the user's own config is ignored)
    gitconfig                GIT_CONFIG_GLOBAL for every git call
    plugin/                  the skill under test, packaged for `claude --plugin-dir`
"""

import itertools
import json
import os
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Mapping

from jj_eval.repo import JJRepo

FIXED_TIMESTAMP = "2026-01-01T00:00:00+00:00"

# Keep auth and provider selection; drop the parent Claude Code session and its host.
KEPT_CLAUDE_VARS = {
    "CLAUDE_CODE_OAUTH_TOKEN",
    "CLAUDE_CODE_USE_BEDROCK",
    "CLAUDE_CODE_USE_VERTEX",
    "CLAUDE_CODE_USE_FOUNDRY",
    "CLAUDE_CONFIG_DIR",
}
STRIPPED_PREFIXES = ("CLAUDE", "SCULPT", "JJ_", "GIT_", "_PYI_")
STRIPPED_VARS = {"AI_AGENT", "IS_SANDBOX", "SESSION_TOKEN"}

SHIM = """#!/bin/bash
{real} "$@"
status=$?
printf '%s\\t%s\\n' "$status" "$(printf '%q ' "$@")" >> {log}
exit $status
"""

EDITOR = """#!/bin/sh
echo "$*" >> {log}
echo "error: no interactive editor is available in this session" >&2
exit 1
"""

JJ_CONFIG = """[user]
name = "Eval User"
email = "eval@example.com"

[ui]
editor = [{editor}]
"""

GIT_CONFIG = """[user]
\tname = Eval User
\temail = eval@example.com
[init]
\tdefaultBranch = main
[advice]
\tdetachedHead = false
"""


def clean_environ() -> dict[str, str]:
    return {
        key: value
        for key, value in os.environ.items()
        if key in KEPT_CLAUDE_VARS or not (key.startswith(STRIPPED_PREFIXES) or key in STRIPPED_VARS)
    }


@dataclass(frozen=True)
class Invocation:
    status: int
    args: str


class Sandbox:
    def __init__(self, root: Path, jj: Path):
        self.root = root
        self.jj = jj
        self.repo_dir = root / "repo"
        self.origin_dir = root / "origin.git"
        self.bin_dir = root / "bin"
        self.jj_config = root / "jj-config.toml"
        self.git_config = root / "gitconfig"
        self.jj_log = root / "jj-invocations.log"
        self.editor_log = root / "editor-invocations.log"
        self._seeds = itertools.count(1)

    @classmethod
    def create(cls, root: Path, jj: Path) -> "Sandbox":
        """Wipe `root` and lay out a fresh sandbox there."""
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=True)
        sandbox = cls(root.resolve(), jj)
        sandbox._write_tooling()
        return sandbox

    def _write_tooling(self) -> None:
        self.bin_dir.mkdir()
        editor = self.bin_dir / "jj-eval-editor"
        editor.write_text(EDITOR.format(log=shlex.quote(str(self.editor_log))))
        shim = self.bin_dir / "jj"
        shim.write_text(SHIM.format(real=shlex.quote(str(self.jj)), log=shlex.quote(str(self.jj_log))))
        for script in (editor, shim):
            script.chmod(0o755)
        self.jj_config.write_text(JJ_CONFIG.format(editor=json.dumps(str(editor))))
        self.git_config.write_text(GIT_CONFIG)

    def _common_env(self) -> dict[str, str]:
        return {
            **clean_environ(),
            "JJ_CONFIG": str(self.jj_config),
            "GIT_CONFIG_GLOBAL": str(self.git_config),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
        }

    def harness_env(self) -> dict[str, str]:
        """Environment for setup and checks: pinned timestamps so setup is reproducible."""
        return {
            **self._common_env(),
            "JJ_TIMESTAMP": FIXED_TIMESTAMP,
            "JJ_OP_TIMESTAMP": FIXED_TIMESTAMP,
            "JJ_OP_HOSTNAME": "eval-host",
            "JJ_OP_USERNAME": "eval",
            "GIT_AUTHOR_DATE": FIXED_TIMESTAMP,
            "GIT_COMMITTER_DATE": FIXED_TIMESTAMP,
        }

    def agent_env(self) -> dict[str, str]:
        """Environment for the agent: the jj shim first on PATH, and no usable editor."""
        editor = str(self.bin_dir / "jj-eval-editor")
        env = self._common_env()
        env.update(
            PATH=f"{self.bin_dir}{os.pathsep}{env.get('PATH', '')}",
            EDITOR=editor,
            VISUAL=editor,
            GIT_EDITOR=editor,
        )
        return env

    def open(self, path: Path) -> JJRepo:
        return JJRepo(path, self.jj, self.harness_env(), self._seeds)

    @cached_property
    def repo(self) -> JJRepo:
        return self.open(self.repo_dir)

    def init_repo(self) -> JJRepo:
        self.repo_dir.mkdir()
        self.repo.jj("git", "init", "--colocate")
        return self.repo

    def clone_origin(self) -> JJRepo:
        self.open(self.root).jj("git", "clone", "--colocate", str(self.origin_dir), self.repo_dir.name)
        return self.repo

    def git(self, *args: str, cwd: Path) -> str:
        return subprocess.run(
            ["git", *args], cwd=cwd, env=self.harness_env(), capture_output=True, text=True, check=True
        ).stdout

    def git_commit(self, cwd: Path, message: str, files: Mapping[str, str | None]) -> str:
        """Commit `files` (None deletes) in the plain git work tree at `cwd`; returns the commit id."""
        for path, content in files.items():
            target = cwd / path
            if content is None:
                self.git("rm", "-q", "--", path, cwd=cwd)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content)
                self.git("add", "--", path, cwd=cwd)
        self.git("commit", "-q", "-m", message, cwd=cwd)
        return self.git("rev-parse", "HEAD", cwd=cwd).strip()

    def install_skill(self, skill_dir: Path) -> Path:
        """Package `skill_dir` as a plugin directory for `claude --plugin-dir`."""
        plugin = self.root / "plugin"
        manifest = plugin / ".claude-plugin" / "plugin.json"
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps({"name": "jujutsu", "version": "0.0.0", "description": "Skill under test"}))
        shutil.copytree(skill_dir, plugin / "skills" / skill_dir.name)
        return plugin

    def jj_invocations(self) -> list[Invocation]:
        """Every jj command the agent ran through the shim, with its exit status."""
        if not self.jj_log.exists():
            return []
        invocations = []
        for line in self.jj_log.read_text().splitlines():
            status, _, args = line.partition("\t")
            invocations.append(Invocation(int(status), args.strip()))
        return invocations

    def editor_invocations(self) -> int:
        return len(self.editor_log.read_text().splitlines()) if self.editor_log.exists() else 0
