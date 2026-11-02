"""Places where jj's defaults or syntax trip people up."""

import hashlib

from jj_eval.repo import require
from jj_eval.scenario import Scenario
from jj_eval.scenarios.fixtures import base_repo, require_file, require_no_conflicts, require_parent, stack


def _dataset() -> bytes:
    rows = ["id,sensor,reading"] + [f"{i},sensor-{i % 17},{(i * 7919) % 10007}" for i in range(150_000)]
    return ("\n".join(rows) + "\n").encode()


DATASET = _dataset()  # about 3 MB, well over jj's default 1 MiB snapshot.max-new-file-size


class CommitLargeFile(Scenario):
    name = "commit-large-file"
    tags = ("edge",)
    prompt = (
        'I just added assets/dataset.csv (about 3 MB). Commit it with the description "Add dataset"; '
        "the whole file has to be in that commit."
    )

    def setup(self, sb):
        base_repo(sb).write("assets/dataset.csv", DATASET)

    def solve(self, sb):
        sb.repo.jj("file", "track", "--include-ignored", "assets/dataset.csv")
        sb.repo.jj("commit", "-m", "Add dataset")

    def check(self, sb):
        repo = sb.repo
        commit = repo.the("Add dataset")
        data = repo.file_bytes(commit.commit_id, "assets/dataset.csv")
        require(data is not None, "assets/dataset.csv is not in the 'Add dataset' commit")
        require(
            hashlib.sha256(data).digest() == hashlib.sha256(DATASET).digest(),
            f"the committed dataset is {len(data)} bytes and differs from the original {len(DATASET)} bytes",
        )
        require_parent(repo, commit, repo.the("Initial import"))


class ResolveRebaseConflict(Scenario):
    name = "resolve-rebase-conflict"
    tags = ("edge",)
    prompt = (
        "Rebase my feature bookmark onto main. groceries.txt will conflict: resolve it by keeping both "
        "additions, main's line first and then mine."
    )
    resolved = "apples\nbananas\ncherries\ndates\n"

    def setup(self, sb):
        repo = base_repo(sb)
        start = repo.commit("Start grocery list", {"groceries.txt": "apples\nbananas\n"})
        cherries = repo.commit("Add cherries", {"groceries.txt": "apples\nbananas\ncherries\n"})
        repo.jj("bookmark", "move", "main", "--to", cherries.change_id)
        repo.jj("new", start.change_id)
        dates = repo.commit("Add dates", {"groceries.txt": "apples\nbananas\ndates\n"})
        repo.jj("bookmark", "create", "feature", "-r", dates.change_id)

    def solve(self, sb):
        repo = sb.repo
        repo.jj("rebase", "-b", "feature", "-o", "main")
        repo.jj("new", "feature")
        repo.write("groceries.txt", self.resolved)
        repo.jj("squash")

    def check(self, sb):
        repo = sb.repo
        dates = repo.the("Add dates")
        require_parent(repo, dates, repo.the("Add cherries"))
        require_no_conflicts(repo)
        require_file(repo, dates, "groceries.txt", self.resolved)
        bookmark = repo.bookmark("feature")
        require(bookmark and bookmark.target == dates.commit_id, "feature should point at 'Add dates'")


class DiscardAwkwardPaths(Scenario):
    name = "discard-awkward-paths"
    tags = ("edge",)
    prompt = (
        'Discard my uncommitted changes to "docs/notes (draft).md" and "~scratch.txt", '
        "but keep all my other uncommitted changes."
    )
    files_v1 = {"docs/notes (draft).md": "draft v1\n", "~scratch.txt": "scratch v1\n", "src/main.txt": "main v1\n"}

    def setup(self, sb):
        repo = base_repo(sb)
        repo.commit("Add notes", self.files_v1)
        for path in self.files_v1:
            repo.write(path, self.files_v1[path].replace("v1", "v2"))

    def solve(self, sb):
        sb.repo.jj("restore", 'root-file:"docs/notes (draft).md"', 'root-file:"~scratch.txt"')

    def check(self, sb):
        repo = sb.repo
        require(repo.get("@").parents == (repo.the("Add notes").commit_id,), "the working copy moved off 'Add notes'")
        require_file(repo, "@", "docs/notes (draft).md", "draft v1\n")
        require_file(repo, "@", "~scratch.txt", "scratch v1\n")
        require_file(repo, "@", "src/main.txt", "main v2\n")


class StopTrackingSecret(Scenario):
    name = "stop-tracking-secret"
    tags = ("edge",)
    prompt = (
        "Stop tracking secrets.env: keep the file on disk, but take it out of version control from now on "
        "and make sure it won't get picked up again."
    )
    secret = "API_KEY=abc123\n"

    def setup(self, sb):
        stack(base_repo(sb), ("Add config", {"config.txt": "debug = false\n", "secrets.env": self.secret}))

    def solve(self, sb):
        sb.repo.write(".gitignore", "secrets.env\n")
        sb.repo.jj("file", "untrack", "secrets.env")

    def check(self, sb):
        repo = sb.repo
        require(repo.read("secrets.env") == self.secret, "secrets.env was changed or deleted on disk")
        require("secrets.env" not in repo.files("@"), "secrets.env is still tracked in the working copy")
        # --no-index: the colocated git index still lists the file from the parent commit.
        ignored = sb.git("check-ignore", "--no-index", "secrets.env", cwd=sb.repo_dir, check=False).strip()
        require(ignored == "secrets.env", "secrets.env is not ignored, so the next snapshot will track it again")
        require_file(repo, "@", "config.txt", "debug = false\n")


class AddWorkspace(Scenario):
    name = "add-workspace"
    tags = ("edge",)
    prompt = (
        "Create a second workspace for this repo at ../repo-docs so I can work on docs in parallel. "
        "Its working copy should start on top of main."
    )

    def setup(self, sb):
        stack(base_repo(sb), ("Add login page", {"src/login.txt": "login form\n"}))

    def solve(self, sb):
        sb.repo.jj("workspace", "add", "-r", "main", "../repo-docs")

    def check(self, sb):
        docs_dir = sb.root / "repo-docs"
        require((docs_dir / ".jj").is_dir(), "../repo-docs is not a jj workspace")
        workspace = sb.open(docs_dir)
        initial = sb.repo.the("Initial import")
        require(workspace.get("@").parents == (initial.commit_id,), "the new workspace should start on top of main")
        require(workspace.read("README.md") is not None, "the new workspace has no files checked out")
        require_no_conflicts(sb.repo)


class TagRelease(Scenario):
    name = "tag-release"
    tags = ("edge",)
    prompt = 'Tag the "Release 1.0" commit as v1.0.'

    def setup(self, sb):
        stack(base_repo(sb), ("Release 1.0", {"VERSION": "1.0\n"}), ("Start 1.1 development", {"VERSION": "1.1-dev\n"}))

    def solve(self, sb):
        sb.repo.jj("tag", "set", "v1.0", "-r", sb.repo.the("Release 1.0").change_id)

    def check(self, sb):
        tagged = sb.git("rev-parse", "--verify", "-q", "refs/tags/v1.0^{commit}", cwd=sb.repo_dir, check=False)
        require(tagged.strip() == sb.repo.the("Release 1.0").commit_id, "v1.0 does not tag the 'Release 1.0' commit")
