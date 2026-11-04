"""Starting repos shared by several scenarios."""

import shutil
import tempfile
from pathlib import Path
from typing import Mapping

from jj_eval.repo import Commit, JJRepo, require
from jj_eval.sandbox import Sandbox

README = "# Widget\n\nA small demo project.\n"
APP = "app v1\n"
INITIAL_FILES = {"README.md": README, "src/app.txt": APP}


def base_repo(sb: Sandbox, colocate: bool = False) -> JJRepo:
    """'Initial import' under a local `main` bookmark, with an empty working-copy commit on top."""
    repo = sb.init_repo(colocate)
    initial = repo.commit("Initial import", INITIAL_FILES)
    repo.jj("bookmark", "create", "main", "-r", initial.change_id)
    return repo


def stack(repo: JJRepo, *commits: tuple[str, Mapping[str, str | None]]) -> list[Commit]:
    """Commit each (message, files) pair on top of the previous one."""
    return [repo.commit(message, files) for message, files in commits]


def cloned_repo(sb: Sandbox, branches: Mapping[str, tuple[str, Mapping[str, str]]] = {}) -> JJRepo:
    """Publish 'Initial import' as main on a bare origin, plus one commit per extra branch, then clone it."""
    upstream = sb.root / "upstream"
    upstream.mkdir()
    sb.git("init", "-q", "-b", "main", cwd=upstream)
    sb.git_commit(upstream, "Initial import", INITIAL_FILES)
    for branch, (message, files) in branches.items():
        sb.git("checkout", "-q", "-b", branch, "main", cwd=upstream)
        sb.git_commit(upstream, message, files)
    sb.git("checkout", "-q", "main", cwd=upstream)
    sb.git("clone", "-q", "--bare", str(upstream), str(sb.origin_dir), cwd=sb.root)
    shutil.rmtree(upstream)
    return sb.clone_origin()


def push_to_origin(sb: Sandbox, message: str, files: Mapping[str, str], branch: str = "main") -> str:
    """Someone else pushes a commit to `branch` on origin. Returns its commit id."""
    with tempfile.TemporaryDirectory() as tmp:
        clone = Path(tmp) / "colleague"
        sb.git("clone", "-q", "--branch", branch, str(sb.origin_dir), str(clone), cwd=sb.root)
        commit_id = sb.git_commit(clone, message, files)
        sb.git("push", "-q", "origin", branch, cwd=clone)
    return commit_id


def origin_ref(sb: Sandbox, ref: str) -> str | None:
    """The commit id `ref` points at in the bare origin, or None if it does not exist there."""
    result = sb.git("for-each-ref", "--format=%(objectname)", f"refs/heads/{ref}", cwd=sb.origin_dir).strip()
    return result or None


def require_no_conflicts(repo: JJRepo, revset: str = "all()") -> None:
    conflicted = [commit.subject or commit.change_id for commit in repo.log(f"conflicts() & ({revset})")]
    require(not conflicted, f"commits still have unresolved conflicts: {conflicted}")


def require_parent(repo: JJRepo, child: Commit, parent: Commit) -> None:
    require(
        child.parents == (parent.commit_id,),
        f"{child.subject!r} should sit directly on {parent.subject!r}, but its parents are {child.parents}",
    )


def require_file(repo: JJRepo, rev: Commit | str, path: str, expected: str | None) -> None:
    commit_id = rev.commit_id if isinstance(rev, Commit) else rev
    label = rev.subject if isinstance(rev, Commit) else rev
    actual = repo.file(commit_id, path)
    require(actual == expected, f"{path} in {label!r} should be {expected!r}, but is {actual!r}")


def require_unchanged_after(repo: JJRepo, commit: Commit, rev: str = "@") -> None:
    """Nothing changed between `commit` and `rev`: any commits in between are empty."""
    changed = repo.diff_paths(commit.commit_id, rev)
    require(not changed, f"{rev} should have the same contents as {commit.subject!r}, but these differ: {changed}")
