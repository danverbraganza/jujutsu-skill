"""The fixed layout inside a task's container, where setup, checks, and reference solutions run.

    /app/repo                          the jj repo the agent works in; not colocated, so git commands fail in it
    /app/origin.git                    bare git remote, for scenarios that push or fetch
    /usr/local/libexec/jj              the jj under test, which the harness calls directly
    /usr/local/bin/jj                  shim that logs each agent jj call, then runs the jj under test
    /logs/agent/jj-invocations.log     what the shim logged
"""

import itertools
import os
import subprocess
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Mapping

from jj_eval.repo import JJRepo

ROOT = Path("/app")
JJ = Path("/usr/local/libexec/jj")
AGENT_LOGS = Path("/logs/agent")
FIXED_TIMESTAMP = "2026-01-01T00:00:00+00:00"
PINNED = {
    "JJ_TIMESTAMP": FIXED_TIMESTAMP,
    "JJ_OP_TIMESTAMP": FIXED_TIMESTAMP,
    "JJ_OP_HOSTNAME": "eval-host",
    "JJ_OP_USERNAME": "eval",
    "GIT_AUTHOR_DATE": FIXED_TIMESTAMP,
    "GIT_COMMITTER_DATE": FIXED_TIMESTAMP,
}


@dataclass(frozen=True)
class Invocation:
    status: int
    args: str


class Sandbox:
    """`deterministic` pins seeds and timestamps, so a scenario's setup builds the same repo every time."""

    def __init__(self, root: Path = ROOT, jj: Path = JJ, agent_logs: Path = AGENT_LOGS, deterministic: bool = False):
        self.root = root
        self.jj = jj
        self.repo_dir = root / "repo"
        self.origin_dir = root / "origin.git"
        self.jj_log = agent_logs / "jj-invocations.log"
        self.editor_log = agent_logs / "editor-invocations.log"
        self._env = {**os.environ, **(PINNED if deterministic else {})}
        self._seeds = itertools.count(1) if deterministic else None

    def open(self, path: Path) -> JJRepo:
        return JJRepo(path, self.jj, self._env, self._seeds)

    @cached_property
    def repo(self) -> JJRepo:
        return self.open(self.repo_dir)

    def init_repo(self, colocate: bool = False) -> JJRepo:
        """Scenarios about using jj and git together set `colocate`; in every other repo, git commands fail."""
        self.repo_dir.mkdir(parents=True)
        self.repo.jj("git", "init", "--colocate" if colocate else "--no-colocate")
        return self.repo

    def clone_origin(self) -> JJRepo:
        self.open(self.root).jj("git", "clone", "--no-colocate", str(self.origin_dir), self.repo_dir.name)
        return self.repo

    def git(self, *args: str, cwd: Path, check: bool = True) -> str:
        return subprocess.run(
            ["git", *args], cwd=cwd, env=self._env, capture_output=True, text=True, check=check
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
