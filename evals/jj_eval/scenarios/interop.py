"""Using jj and git together, in a colocated repo: the only scenarios where git commands work."""

from jj_eval.repo import require
from jj_eval.scenario import Scenario
from jj_eval.scenarios.fixtures import base_repo


class CheckOutBranchInGit(Scenario):
    name = "check-out-branch-in-git"
    tags = ("interop",)
    prompt = (
        "Our release script only understands git: it needs the release branch checked out, with a clean "
        "working tree. Check out release in git for it, without losing my uncommitted work."
    )
    search = "search(query)\n"
    app = "app v1\nsearch enabled\n"

    def setup(self, sb):
        repo = base_repo(sb, colocate=True)
        release = repo.commit("Prepare release 1.0", {"VERSION": "1.0\n"})
        repo.jj("bookmark", "create", "release", "-r", release.change_id)
        repo.jj("new", "main")
        repo.write("src/search.txt", self.search)
        repo.write("src/app.txt", self.app)
        repo.jj("status")  # snapshot the uncommitted work into the working-copy commit

    def solve(self, sb):
        sb.repo.jj("new")  # move the work out of the working copy, so git sees a clean tree
        sb.git("checkout", "-q", "release", cwd=sb.repo_dir)

    def check(self, sb):
        # What the release script sees, read before any jj command runs in the repo.
        head = sb.git("symbolic-ref", "-q", "HEAD", cwd=sb.repo_dir, check=False).strip()
        require(head == "refs/heads/release", f"git should have release checked out, but HEAD is {head or 'detached'}")
        dirty = sb.git("status", "--porcelain", cwd=sb.repo_dir).strip()
        require(not dirty, f"git's working tree should be clean, but git status shows {dirty!r}")
        checked_out = sb.git("rev-parse", "HEAD", cwd=sb.repo_dir).strip()
        repo = sb.repo
        require(checked_out == repo.the("Prepare release 1.0").commit_id, "release no longer points at its commit")
        kept = [
            commit for commit in repo.log()
            if repo.file(commit.commit_id, "src/search.txt") == self.search
            and repo.file(commit.commit_id, "src/app.txt") == self.app
        ]
        require(kept, "the uncommitted work was lost: no commit has both src/search.txt and the src/app.txt edit")
