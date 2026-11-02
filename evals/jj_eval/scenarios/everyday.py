"""Day-to-day requests, drawn from the commands jj users reach for most often."""

from jj_eval.repo import require
from jj_eval.scenario import Scenario
from jj_eval.scenarios.fixtures import (
    APP,
    base_repo,
    require_file,
    require_no_conflicts,
    require_parent,
    require_unchanged_after,
    stack,
)


class CommitWorkingCopy(Scenario):
    name = "commit-working-copy"
    tags = ("everyday",)
    prompt = 'Commit my current changes with the message "Add healthcheck endpoint".'

    def setup(self, sb):
        repo = base_repo(sb)
        repo.write("src/app.txt", "app v2\n")
        repo.write("src/health.txt", "GET /healthz -> 200\n")

    def solve(self, sb):
        sb.repo.jj("commit", "-m", "Add healthcheck endpoint")

    def check(self, sb):
        repo = sb.repo
        commit = repo.the("Add healthcheck endpoint")
        require_parent(repo, commit, repo.the("Initial import"))
        require_file(repo, commit, "src/app.txt", "app v2\n")
        require_file(repo, commit, "src/health.txt", "GET /healthz -> 200\n")
        require(repo.log(f"{commit.commit_id} & ::@"), "the new commit should be in the working copy's history")
        require_unchanged_after(repo, commit)


class RewordOlderCommit(Scenario):
    name = "reword-older-commit"
    tags = ("everyday",)
    prompt = 'Change the description of the commit currently described "fix stuff" to "Fix off-by-one in pagination".'

    def setup(self, sb):
        stack(
            base_repo(sb),
            ("Add pagination", {"src/pager.txt": "pages = range(1, n)\n"}),
            ("fix stuff", {"src/pager.txt": "pages = range(1, n + 1)\n"}),
            ("Add footer", {"src/footer.txt": "footer\n"}),
        )

    def solve(self, sb):
        fix = sb.repo.the("fix stuff")
        sb.repo.jj("describe", "-r", fix.change_id, "-m", "Fix off-by-one in pagination")

    def check(self, sb):
        repo = sb.repo
        require(not repo.by_subject("fix stuff"), "a commit is still described 'fix stuff'")
        fixed = repo.the("Fix off-by-one in pagination")
        require(fixed.description == "Fix off-by-one in pagination", f"full description is {fixed.description!r}")
        require_parent(repo, fixed, repo.the("Add pagination"))
        require_parent(repo, repo.the("Add footer"), fixed)
        require(repo.changed_paths(fixed.commit_id) == {"src/pager.txt"}, "the reworded commit's changes moved")
        require_file(repo, fixed, "src/pager.txt", "pages = range(1, n + 1)\n")


class StartChangeOnMain(Scenario):
    name = "start-change-on-main"
    tags = ("everyday",)
    prompt = (
        "Leave what I'm working on as it is, and start a fresh change directly on top of main, described "
        '"Refresh README", with a bookmark named docs-refresh on it. My working copy should be that new change.'
    )

    def setup(self, sb):
        repo = base_repo(sb)
        repo.commit("Add settings page", {"src/settings.txt": "theme = light\n"})
        repo.write("src/settings.txt", "theme = light\nfont = large\n")

    def solve(self, sb):
        sb.repo.jj("new", "main", "-m", "Refresh README")
        sb.repo.jj("bookmark", "create", "docs-refresh", "-r", "@")

    def check(self, sb):
        repo = sb.repo
        refresh = repo.the("Refresh README")
        require_parent(repo, refresh, repo.the("Initial import"))
        require(refresh.empty, "the new change should not contain any file changes yet")
        bookmark = repo.bookmark("docs-refresh")
        require(bookmark and bookmark.target == refresh.commit_id, "docs-refresh should point at the new change")
        working_copy = repo.get("@")
        require(
            working_copy.commit_id == refresh.commit_id
            or (working_copy.empty and working_copy.parents == (refresh.commit_id,)),
            "the working copy should be the new change",
        )
        in_progress = "theme = light\nfont = large\n"
        require(
            any(repo.file(c.commit_id, "src/settings.txt") == in_progress for c in repo.log()),
            "the in-progress settings edit was lost",
        )


class CreateBookmark(Scenario):
    name = "create-bookmark"
    tags = ("everyday",)
    prompt = "Create a bookmark called feature-login on the commit that adds the login page."

    def setup(self, sb):
        stack(base_repo(sb), ("Add login page", {"src/login.txt": "login form\n"}))

    def solve(self, sb):
        sb.repo.jj("bookmark", "create", "feature-login", "-r", sb.repo.the("Add login page").change_id)

    def check(self, sb):
        repo = sb.repo
        login = repo.the("Add login page")
        bookmark = repo.bookmark("feature-login")
        require(bookmark, "there is no feature-login bookmark")
        require(bookmark.target == login.commit_id, "feature-login does not point at the login page commit")
        require_file(repo, login, "src/login.txt", "login form\n")


class MoveBookmarkForward(Scenario):
    name = "move-bookmark-forward"
    tags = ("everyday",)
    prompt = (
        'I added two commits on top of my api-client bookmark ("Add retries" and "Add timeouts"). '
        "Update the bookmark so it includes them."
    )

    def setup(self, sb):
        repo = base_repo(sb)
        client = repo.commit("Add API client", {"src/client.txt": "client\n"})
        repo.jj("bookmark", "create", "api-client", "-r", client.change_id)
        stack(repo, ("Add retries", {"src/retry.txt": "retries = 3\n"}), ("Add timeouts", {"src/timeout.txt": "30s\n"}))

    def solve(self, sb):
        sb.repo.jj("bookmark", "move", "api-client", "--to", sb.repo.the("Add timeouts").change_id)

    def check(self, sb):
        repo = sb.repo
        bookmark = repo.bookmark("api-client")
        require(bookmark, "the api-client bookmark is gone")
        require(bookmark.target == repo.the("Add timeouts").commit_id, "api-client should point at 'Add timeouts'")


class EditEarlierCommit(Scenario):
    name = "edit-earlier-commit"
    tags = ("everyday",)
    prompt = (
        'In the "Add config" commit, a few commits back, change the port in config.txt from 8080 to 9090. '
        "The later commits should stay as they are, on top of the fixed commit."
    )
    fixed_config = "host = localhost\nport = 9090\n"

    def setup(self, sb):
        stack(
            base_repo(sb),
            ("Add config", {"config.txt": "host = localhost\nport = 8080\n"}),
            ("Add server", {"server.txt": "serve(config)\n"}),
            ("Add logging", {"logging.txt": "level = info\n"}),
        )

    def solve(self, sb):
        repo = sb.repo
        repo.jj("new", repo.the("Add config").change_id)
        repo.write("config.txt", self.fixed_config)
        repo.jj("squash")
        repo.jj("new", repo.the("Add logging").change_id)

    def check(self, sb):
        repo = sb.repo
        config, server, logging = (repo.the(s) for s in ("Add config", "Add server", "Add logging"))
        require_file(repo, config, "config.txt", self.fixed_config)
        require(repo.changed_paths(config.commit_id) == {"config.txt"}, "'Add config' should only touch config.txt")
        require_parent(repo, server, config)
        require_parent(repo, logging, server)
        require_file(repo, logging, "config.txt", self.fixed_config)
        require_file(repo, logging, "logging.txt", "level = info\n")
        require_no_conflicts(repo)


class RestoreFileFromOldCommit(Scenario):
    name = "restore-file-from-old-commit"
    tags = ("everyday",)
    prompt = (
        'Bring src/app.txt back to exactly how it was in the "Initial import" commit, as a new change in my '
        "working copy. Don't rewrite any existing commits."
    )

    def setup(self, sb):
        stack(
            base_repo(sb),
            ("Rewrite app", {"src/app.txt": "app v2\n"}),
            ("Tweak app", {"src/app.txt": "app v3\n", "src/extra.txt": "extra\n"}),
        )

    def solve(self, sb):
        sb.repo.jj("restore", "--from", sb.repo.the("Initial import").change_id, "src/app.txt")

    def check(self, sb):
        repo = sb.repo
        tweak = repo.the("Tweak app")
        require_file(repo, "@", "src/app.txt", APP)
        require_file(repo, repo.the("Rewrite app"), "src/app.txt", "app v2\n")
        require_file(repo, tweak, "src/app.txt", "app v3\n")
        require(repo.log(f"{tweak.commit_id} & ::@"), "the working copy should still build on 'Tweak app'")
        changed = repo.diff_paths(tweak.commit_id, "@")
        require(changed == {"src/app.txt"}, f"only src/app.txt should change on top of 'Tweak app', got {changed}")


class AbandonMiddleCommit(Scenario):
    name = "abandon-middle-commit"
    tags = ("everyday",)
    prompt = 'Throw away the "Experimental hack" commit completely, but keep the commits before and after it.'

    def setup(self, sb):
        stack(
            base_repo(sb),
            ("Add A", {"a.txt": "a\n"}),
            ("Experimental hack", {"hack.txt": "hack\n"}),
            ("Add B", {"b.txt": "b\n"}),
        )

    def solve(self, sb):
        sb.repo.jj("abandon", sb.repo.the("Experimental hack").change_id)

    def check(self, sb):
        repo = sb.repo
        require(not repo.by_subject("Experimental hack"), "'Experimental hack' is still there")
        add_b = repo.the("Add B")
        require_parent(repo, add_b, repo.the("Add A"))
        require_file(repo, add_b, "b.txt", "b\n")
        require_file(repo, add_b, "hack.txt", None)
        require_file(repo, "@", "hack.txt", None)
        require_no_conflicts(repo)


class RecoverAbandonedCommit(Scenario):
    name = "recover-abandoned-commit"
    tags = ("everyday",)
    prompt = 'I accidentally abandoned my "Add parser" commit a moment ago. Please bring it back.'

    def setup(self, sb):
        repo = base_repo(sb)
        parser = repo.commit("Add parser", {"src/parser.txt": "parse tokens\n"})
        repo.jj("abandon", parser.change_id)

    def solve(self, sb):
        sb.repo.jj("undo")

    def check(self, sb):
        repo = sb.repo
        parser = repo.the("Add parser")
        require_file(repo, parser, "src/parser.txt", "parse tokens\n")
        require_parent(repo, parser, repo.the("Initial import"))
