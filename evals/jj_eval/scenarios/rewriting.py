"""Reshaping history: rebasing, squashing, splitting, reordering, reverting, merging."""

from jj_eval.repo import require
from jj_eval.scenario import Scenario
from jj_eval.scenarios.fixtures import (
    base_repo,
    require_file,
    require_no_conflicts,
    require_parent,
    require_unchanged_after,
    stack,
)

README_V2 = "# Widget\n\nA small demo project.\n\nNow with a parser.\n"


class RebaseTreeOntoMain(Scenario):
    name = "rebase-tree-onto-main"
    tags = ("rewriting",)
    prompt = (
        "main has moved on since I started. Rebase all of my parser work onto main: the \"Add parser\" commit "
        "and everything built on top of it."
    )

    def setup(self, sb):
        repo = base_repo(sb)
        parser = repo.commit("Add parser", {"src/parser.txt": "parse tokens\n"})
        tests = repo.commit("Add parser tests", {"tests/parser.txt": "test parse\n"})
        repo.jj("bookmark", "create", "parser-tests", "-r", tests.change_id)
        repo.jj("new", parser.change_id)
        docs = repo.commit("Add parser docs", {"docs/parser.md": "# Parser\n"})
        repo.jj("bookmark", "create", "parser-docs", "-r", docs.change_id)
        repo.jj("new", "main")
        update = repo.commit("Update README", {"README.md": README_V2})
        repo.jj("bookmark", "move", "main", "--to", update.change_id)
        repo.jj("new", tests.change_id)

    def solve(self, sb):
        sb.repo.jj("rebase", "-s", sb.repo.the("Add parser").change_id, "-o", "main")

    def check(self, sb):
        repo = sb.repo
        update = repo.the("Update README")
        parser, tests, docs = (repo.the(s) for s in ("Add parser", "Add parser tests", "Add parser docs"))
        require_parent(repo, parser, update)
        require_parent(repo, tests, parser)
        require_parent(repo, docs, parser)
        for name, commit in (("main", update), ("parser-tests", tests), ("parser-docs", docs)):
            bookmark = repo.bookmark(name)
            require(bookmark and bookmark.target == commit.commit_id, f"{name} should point at {commit.subject!r}")
        require_file(repo, tests, "README.md", README_V2)
        require_file(repo, tests, "tests/parser.txt", "test parse\n")
        require_file(repo, docs, "docs/parser.md", "# Parser\n")
        require_no_conflicts(repo)


class SquashIntoParent(Scenario):
    name = "squash-into-parent"
    tags = ("rewriting",)
    prompt = 'Squash the "WIP" commit into its parent "Add parser", keeping the "Add parser" description.'

    def setup(self, sb):
        stack(
            base_repo(sb),
            ("Add parser", {"src/parser.txt": "parse tokens\n"}),
            ("WIP", {"src/parser.txt": "parse tokens\nparse trees\n"}),
        )

    def solve(self, sb):
        sb.repo.jj("squash", "-r", sb.repo.the("WIP").change_id, "--use-destination-message")

    def check(self, sb):
        repo = sb.repo
        require(not [c for c in repo.log() if "WIP" in c.description], "a commit still mentions WIP")
        parser = repo.the("Add parser")
        require(parser.description == "Add parser", f"the description should stay 'Add parser', is {parser.description!r}")
        require_parent(repo, parser, repo.the("Initial import"))
        require_file(repo, parser, "src/parser.txt", "parse tokens\nparse trees\n")
        require_unchanged_after(repo, parser)


class SquashFileIntoAncestor(Scenario):
    name = "squash-file-into-ancestor"
    tags = ("rewriting",)
    prompt = (
        "My working copy has two unrelated edits. Move the change to tests/test_parser.txt into the "
        '"Add parser tests" commit, and leave the src/cli.txt change in my working copy.'
    )

    def setup(self, sb):
        repo = base_repo(sb)
        stack(
            repo,
            ("Add parser", {"src/parser.txt": "parse tokens\n"}),
            ("Add parser tests", {"tests/test_parser.txt": "test one\n"}),
            ("Add CLI", {"src/cli.txt": "cli\n"}),
        )
        repo.write("tests/test_parser.txt", "test one\ntest two\n")
        repo.write("src/cli.txt", "cli\ncli --verbose\n")

    def solve(self, sb):
        sb.repo.jj("squash", "--into", sb.repo.the("Add parser tests").change_id, "tests/test_parser.txt")

    def check(self, sb):
        repo = sb.repo
        tests, cli = repo.the("Add parser tests"), repo.the("Add CLI")
        require_file(repo, tests, "tests/test_parser.txt", "test one\ntest two\n")
        require_parent(repo, cli, tests)
        require_file(repo, cli, "src/cli.txt", "cli\n")
        require(repo.get("@").parents == (cli.commit_id,), "the working copy should still sit on 'Add CLI'")
        changed = repo.changed_paths("@")
        require(changed == {"src/cli.txt"}, f"the working copy should only change src/cli.txt, but changes {changed}")
        require_file(repo, "@", "src/cli.txt", "cli\ncli --verbose\n")
        require_no_conflicts(repo)


class AbsorbFixups(Scenario):
    name = "absorb-fixups"
    tags = ("rewriting",)
    prompt = (
        "My working copy fixes a typo in greeting.txt and another in farewell.txt. Fold each fix into the "
        "commit that originally added that file."
    )

    def setup(self, sb):
        repo = base_repo(sb)
        stack(
            repo,
            ("Add greeting", {"greeting.txt": "Helo, world\n"}),
            ("Add farewell", {"farewell.txt": "Goodbey, world\n"}),
        )
        repo.write("greeting.txt", "Hello, world\n")
        repo.write("farewell.txt", "Goodbye, world\n")

    def solve(self, sb):
        sb.repo.jj("absorb")

    def check(self, sb):
        repo = sb.repo
        greeting, farewell = repo.the("Add greeting"), repo.the("Add farewell")
        require_file(repo, greeting, "greeting.txt", "Hello, world\n")
        require(repo.changed_paths(greeting.commit_id) == {"greeting.txt"}, "'Add greeting' changes other files")
        require_parent(repo, farewell, greeting)
        require_file(repo, farewell, "farewell.txt", "Goodbye, world\n")
        require(repo.changed_paths(farewell.commit_id) == {"farewell.txt"}, "'Add farewell' changes other files")
        require_unchanged_after(repo, farewell)


class SplitByPath(Scenario):
    name = "split-by-path"
    tags = ("rewriting",)
    prompt = (
        'My working-copy commit mixes code and docs. Split it into two commits: "Add search" with only '
        'src/search.txt, and "Document search" with only docs/search.md.'
    )

    def setup(self, sb):
        repo = base_repo(sb)
        repo.write("src/search.txt", "search(query)\n")
        repo.write("docs/search.md", "# Search\n")
        repo.jj("describe", "-m", "Add search and docs")

    def solve(self, sb):
        sb.repo.jj("split", "-m", "Add search", "src/search.txt")
        sb.repo.jj("describe", "-m", "Document search")

    def check(self, sb):
        repo = sb.repo
        code, docs = repo.the("Add search"), repo.the("Document search")
        require(repo.changed_paths(code.commit_id) == {"src/search.txt"}, "'Add search' should only add src/search.txt")
        require(repo.changed_paths(docs.commit_id) == {"docs/search.md"}, "'Document search' should only add the doc")
        initial = repo.the("Initial import").commit_id
        require(
            (code.parents == (initial,) and docs.parents == (code.commit_id,))
            or (docs.parents == (initial,) and code.parents == (docs.commit_id,)),
            "the two commits should form one line on top of 'Initial import'",
        )
        require(not repo.by_subject("Add search and docs"), "the combined commit is still there")
        require_file(repo, code, "src/search.txt", "search(query)\n")
        require_file(repo, docs, "docs/search.md", "# Search\n")


class ReorderCommits(Scenario):
    name = "reorder-commits"
    tags = ("rewriting",)
    prompt = (
        'Reorder my commits so "Fix typo in README" comes first, directly on top of "Initial import", '
        'followed by "Add feature X".'
    )
    fixed_readme = "# Widget\n\nA small demonstration project.\n"

    def setup(self, sb):
        stack(
            base_repo(sb),
            ("Add feature X", {"src/x.txt": "x\n"}),
            ("Fix typo in README", {"README.md": self.fixed_readme}),
        )

    def solve(self, sb):
        repo = sb.repo
        repo.jj("rebase", "-r", repo.the("Fix typo in README").change_id, "-B", repo.the("Add feature X").change_id)

    def check(self, sb):
        repo = sb.repo
        typo, feature = repo.the("Fix typo in README"), repo.the("Add feature X")
        require_parent(repo, typo, repo.the("Initial import"))
        require_parent(repo, feature, typo)
        require(repo.changed_paths(typo.commit_id) == {"README.md"}, "'Fix typo in README' should only touch README")
        require(repo.changed_paths(feature.commit_id) == {"src/x.txt"}, "'Add feature X' should only add src/x.txt")
        require_file(repo, feature, "README.md", self.fixed_readme)
        require_no_conflicts(repo)


class RevertCommit(Scenario):
    name = "revert-commit"
    tags = ("rewriting",)
    prompt = (
        'Revert the "Add flaky test" commit: add a new commit on top of my current work that undoes it, '
        "and keep the original commits exactly as they are."
    )

    def setup(self, sb):
        stack(
            base_repo(sb),
            ("Add flaky test", {"tests/flaky.txt": "sometimes fails\n"}),
            ("Add docs", {"docs/guide.md": "# Guide\n"}),
        )

    def solve(self, sb):
        sb.repo.jj("revert", "-r", sb.repo.the("Add flaky test").change_id, "-B", "@")

    def check(self, sb):
        repo = sb.repo
        flaky, docs = repo.the("Add flaky test"), repo.the("Add docs")
        require_parent(repo, flaky, repo.the("Initial import"))
        require_parent(repo, docs, flaky)
        require_file(repo, flaky, "tests/flaky.txt", "sometimes fails\n")
        reverts = [
            c
            for c in repo.log(f"{docs.commit_id}:: ~ {docs.commit_id}")
            if repo.diff_paths(docs.commit_id, c.commit_id) == {"tests/flaky.txt"}
            and repo.file(c.commit_id, "tests/flaky.txt") is None
        ]
        require(reverts, "no commit on top of 'Add docs' removes tests/flaky.txt and keeps everything else")


class MergeTwoBookmarks(Scenario):
    name = "merge-two-bookmarks"
    tags = ("rewriting",)
    prompt = 'Create a merge commit that combines feature-a and feature-b, described "Merge feature-a and feature-b".'

    def setup(self, sb):
        repo = base_repo(sb)
        a = repo.commit("Add A", {"a.txt": "a\n"})
        repo.jj("bookmark", "create", "feature-a", "-r", a.change_id)
        repo.jj("new", "main")
        b = repo.commit("Add B", {"b.txt": "b\n"})
        repo.jj("bookmark", "create", "feature-b", "-r", b.change_id)

    def solve(self, sb):
        sb.repo.jj("new", "feature-a", "feature-b", "-m", "Merge feature-a and feature-b")

    def check(self, sb):
        repo = sb.repo
        merge = repo.the("Merge feature-a and feature-b")
        parents = {repo.the("Add A").commit_id, repo.the("Add B").commit_id}
        require(set(merge.parents) == parents, "the merge commit's parents should be exactly 'Add A' and 'Add B'")
        require_file(repo, merge, "a.txt", "a\n")
        require_file(repo, merge, "b.txt", "b\n")
        require_no_conflicts(repo)


class SetCommitAuthor(Scenario):
    name = "set-commit-author"
    tags = ("rewriting",)
    prompt = (
        'Set the author of the "Add docs" commit to Ada Lovelace <ada@example.com>. '
        "Keep its description and changes as they are."
    )

    def setup(self, sb):
        stack(base_repo(sb), ("Add docs", {"docs/index.md": "# Docs\n"}))

    def solve(self, sb):
        sb.repo.jj("metaedit", "-r", sb.repo.the("Add docs").change_id, "--author", "Ada Lovelace <ada@example.com>")

    def check(self, sb):
        repo = sb.repo
        docs = repo.the("Add docs")
        require(docs.author == "Ada Lovelace <ada@example.com>", f"the author is {docs.author!r}")
        require(docs.description == "Add docs", f"the description changed to {docs.description!r}")
        require(repo.changed_paths(docs.commit_id) == {"docs/index.md"}, "the commit's changes moved")
        require_parent(repo, docs, repo.the("Initial import"))
