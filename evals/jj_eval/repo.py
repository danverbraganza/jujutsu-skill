"""A thin wrapper over the jj CLI for building scenario repos and inspecting their end state."""

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Mapping

FIELD = "\x1f"
RECORD = "\x1e"


def _template(fields: list[str]) -> str:
    return ' ++ "\\x1f" ++ '.join(fields) + ' ++ "\\x1e"'


COMMIT_TEMPLATE = _template(
    [
        "change_id",
        "commit_id",
        'parents.map(|p| p.commit_id()).join(",")',
        'local_bookmarks.map(|b| b.name()).join(",")',
        'if(empty, "1", "0")',
        'if(conflict, "1", "0")',
        'if(current_working_copy, "1", "0")',
        'author.name() ++ " <" ++ author.email() ++ ">"',
        "description",
    ]
)

BOOKMARK_TEMPLATE = _template(
    [
        "name",
        "remote",
        'if(normal_target, normal_target.commit_id(), "")',
        'if(tracked, "1", "0")',
        'if(present, "1", "0")',
    ]
)


class CheckFailure(AssertionError):
    """The repo's end state does not match what the scenario asked for."""


def require(condition: object, message: str) -> None:
    if not condition:
        raise CheckFailure(message)


class JJError(RuntimeError):
    pass


@dataclass(frozen=True)
class Commit:
    change_id: str
    commit_id: str
    parents: tuple[str, ...]
    bookmarks: tuple[str, ...]
    empty: bool
    conflict: bool
    working_copy: bool
    author: str
    description: str

    @property
    def subject(self) -> str:
        return self.description.split("\n", 1)[0]

    @classmethod
    def parse(cls, record: str) -> "Commit":
        change_id, commit_id, parents, bookmarks, empty, conflict, wc, author, description = record.split(FIELD)
        return cls(
            change_id=change_id,
            commit_id=commit_id,
            parents=tuple(filter(None, parents.split(","))),
            bookmarks=tuple(filter(None, bookmarks.split(","))),
            empty=empty == "1",
            conflict=conflict == "1",
            working_copy=wc == "1",
            author=author,
            description=description.rstrip("\n"),
        )


@dataclass(frozen=True)
class Bookmark:
    name: str
    remote: str  # "" for the local bookmark
    target: str | None  # None when absent or conflicted
    tracked: bool
    present: bool

    @classmethod
    def parse(cls, record: str) -> "Bookmark":
        name, remote, target, tracked, present = record.split(FIELD)
        return cls(name, remote, target or None, tracked == "1", present == "1")


def fileset_literal(path: str) -> str:
    """Quote `path` so jj never parses it as a fileset expression."""
    return "root-file:" + json.dumps(path, ensure_ascii=False)


def _records(output: str) -> list[str]:
    return [record for record in output.split(RECORD) if record.strip("\n")]


class JJRepo:
    """One jj workspace. Every command gets a fresh, deterministic randomness seed."""

    def __init__(self, root: Path, jj: Path, env: Mapping[str, str], seeds: Iterator[int]):
        self.root = root
        self._jj = jj
        self._env = dict(env)
        self._seeds = seeds

    def run(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
        env = {**self._env, "JJ_RANDOMNESS_SEED": str(next(self._seeds))}
        result = subprocess.run(
            [str(self._jj), *args], cwd=self.root, env=env, capture_output=True, stdin=subprocess.DEVNULL
        )
        if check and result.returncode != 0:
            stderr = result.stderr.decode(errors="replace").strip()
            raise JJError(f"jj {' '.join(args)} exited {result.returncode}: {stderr}")
        return result

    def jj(self, *args: str) -> str:
        return self.run(*args).stdout.decode()

    def write(self, path: str, content: str | bytes) -> None:
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content.encode() if isinstance(content, str) else content)

    def read(self, path: str) -> str | None:
        target = self.root / path
        return target.read_text() if target.exists() else None

    def commit(self, message: str, files: Mapping[str, str | bytes | None] = {}) -> Commit:
        """Write `files` into the working copy (None deletes), then `jj commit` them as `message`."""
        for path, content in files.items():
            if content is None:
                (self.root / path).unlink()
            else:
                self.write(path, content)
        self.jj("commit", "-m", message)
        return self.get("@-")

    def log(self, revset: str = "all() ~ root()") -> list[Commit]:
        output = self.jj("log", "--no-graph", "-r", revset, "-T", COMMIT_TEMPLATE)
        return [Commit.parse(record) for record in _records(output)]

    def get(self, revset: str) -> Commit:
        commits = self.log(revset)
        require(len(commits) == 1, f"revset {revset!r} resolved to {len(commits)} commits, expected 1")
        return commits[0]

    def by_subject(self, subject: str) -> list[Commit]:
        return [commit for commit in self.log() if commit.subject == subject]

    def the(self, subject: str) -> Commit:
        """The single visible commit whose first description line is `subject`."""
        matches = self.by_subject(subject)
        require(len(matches) == 1, f"expected one visible commit described {subject!r}, found {len(matches)}")
        return matches[0]

    def files(self, rev: str) -> set[str]:
        return set(self.jj("file", "list", "-r", rev).splitlines())

    def file_bytes(self, rev: str, path: str) -> bytes | None:
        if path not in self.files(rev):
            return None
        return self.run("file", "show", "-r", rev, fileset_literal(path)).stdout

    def file(self, rev: str, path: str) -> str | None:
        data = self.file_bytes(rev, path)
        return None if data is None else data.decode()

    def changed_paths(self, rev: str) -> set[str]:
        return set(self.jj("diff", "-r", rev, "--name-only").splitlines())

    def diff_paths(self, from_rev: str, to_rev: str) -> set[str]:
        return set(self.jj("diff", "--from", from_rev, "--to", to_rev, "--name-only").splitlines())

    def bookmarks(self) -> list[Bookmark]:
        output = self.jj("bookmark", "list", "--all-remotes", "-T", BOOKMARK_TEMPLATE)
        return [b for b in map(Bookmark.parse, _records(output)) if b.remote != "git"]

    def bookmark(self, name: str, remote: str = "") -> Bookmark | None:
        """The named local bookmark (or remote-tracking bookmark), if present."""
        for bookmark in self.bookmarks():
            if bookmark.name == name and bookmark.remote == remote and bookmark.present:
                return bookmark
        return None
