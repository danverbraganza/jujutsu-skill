"""Working with a git remote: pushing, fetching, and dropping someone else's branch."""

from jj_eval.repo import require
from jj_eval.scenario import Scenario
from jj_eval.scenarios.fixtures import cloned_repo, origin_ref, push_to_origin, require_file

README_V2 = "# Widget\n\nA small demo project.\n\nNow on main.\n"


class PushNewBookmark(Scenario):
    name = "push-new-bookmark"
    tags = ("remote",)
    prompt = "Push my search bookmark to origin."

    def setup(self, sb):
        repo = cloned_repo(sb)
        search = repo.commit("Add search", {"src/search.txt": "search(query)\n"})
        repo.jj("bookmark", "create", "search", "-r", search.change_id)

    def solve(self, sb):
        sb.repo.jj("bookmark", "track", "search", "--remote", "origin")
        sb.repo.jj("git", "push", "-b", "search")

    def check(self, sb):
        search = sb.repo.the("Add search")
        require(origin_ref(sb, "search") == search.commit_id, "origin's search branch is not at 'Add search'")
        bookmark = sb.repo.bookmark("search")
        require(bookmark and bookmark.target == search.commit_id, "the local search bookmark moved")


class PushUndescribedChange(Scenario):
    name = "push-undescribed-change"
    tags = ("remote",)
    prompt = "Push my current change to origin as a new branch named quick-fix. Give it a sensible commit message."
    fixed_readme = "# Widget\n\nA small demonstration project.\n"

    def setup(self, sb):
        cloned_repo(sb).write("README.md", self.fixed_readme)

    def solve(self, sb):
        repo = sb.repo
        repo.jj("describe", "-m", "Reword the README")
        repo.jj("bookmark", "create", "quick-fix", "-r", "@")
        repo.jj("bookmark", "track", "quick-fix", "--remote", "origin")
        repo.jj("git", "push", "-b", "quick-fix")

    def check(self, sb):
        pushed = origin_ref(sb, "quick-fix")
        require(pushed, "origin has no quick-fix branch")
        message = sb.git("log", "-1", "--format=%B", pushed, cwd=sb.origin_dir).strip()
        require(message, "the pushed commit has no message")
        readme = sb.git("show", f"{pushed}:README.md", cwd=sb.origin_dir)
        require(readme == self.fixed_readme, "the pushed commit does not contain the README change")
        parent = sb.git("rev-parse", f"{pushed}^", cwd=sb.origin_dir).strip()
        require(parent == origin_ref(sb, "main"), "quick-fix should be a single commit on top of main")


class FetchAndRebase(Scenario):
    name = "fetch-and-rebase"
    tags = ("remote",)
    prompt = "Fetch the latest changes from origin and rebase my feature bookmark onto the updated main."

    def setup(self, sb):
        repo = cloned_repo(sb)
        feature = repo.commit("Add feature", {"src/feature.txt": "feature\n"})
        repo.jj("bookmark", "create", "feature", "-r", feature.change_id)
        push_to_origin(sb, "Update README", {"README.md": README_V2})

    def solve(self, sb):
        sb.repo.jj("git", "fetch")
        sb.repo.jj("rebase", "-b", "feature", "-o", "main")

    def check(self, sb):
        repo = sb.repo
        upstream = origin_ref(sb, "main")
        main = repo.bookmark("main")
        require(main and main.target == upstream, "local main does not match origin's main")
        feature = repo.the("Add feature")
        require(feature.parents == (upstream,), "'Add feature' should sit directly on the updated main")
        bookmark = repo.bookmark("feature")
        require(bookmark and bookmark.target == feature.commit_id, "feature should point at 'Add feature'")
        require_file(repo, feature, "README.md", README_V2)
        require_file(repo, feature, "src/feature.txt", "feature\n")


class ForgetColleagueBookmark(Scenario):
    name = "forget-colleague-bookmark"
    tags = ("remote",)
    prompt = (
        "I'm done reviewing my colleague's colleague-wip branch. Remove it from my local repo, but it has to "
        "stay on origin: don't delete it there, now or the next time I push."
    )

    def setup(self, sb):
        repo = cloned_repo(sb, {"colleague-wip": ("Colleague WIP", {"wip.txt": "wip\n"})})
        repo.jj("bookmark", "track", "colleague-wip", "--remote", "origin")

    def solve(self, sb):
        sb.repo.jj("bookmark", "forget", "colleague-wip")

    def check(self, sb):
        repo = sb.repo
        require(repo.bookmark("colleague-wip") is None, "the local colleague-wip bookmark is still there")
        remote = repo.bookmark("colleague-wip", remote="origin")
        require(
            not (remote and remote.tracked),
            "colleague-wip@origin is still tracked with no local bookmark, so the next push deletes it on origin",
        )
        require(origin_ref(sb, "colleague-wip"), "colleague-wip was deleted on origin")
