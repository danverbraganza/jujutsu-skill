from jj_eval.sandbox import Sandbox


def test_commit_and_query_round_trip(sandbox):
    repo = sandbox.init_repo()
    first = repo.commit("Initial import", {"README.md": "# Widget\n"})
    repo.jj("bookmark", "create", "main", "-r", first.change_id)
    second = repo.commit("Add login page\n\nWith a body.", {"src/login.txt": "login\n"})

    assert second.subject == "Add login page"
    assert second.description == "Add login page\n\nWith a body."
    assert second.parents == (first.commit_id,)
    assert repo.the("Initial import").bookmarks == ("main",)
    assert repo.file(second.commit_id, "src/login.txt") == "login\n"
    assert repo.file(first.commit_id, "src/login.txt") is None
    assert repo.changed_paths(second.commit_id) == {"src/login.txt"}
    working_copy = repo.get("@")
    assert working_copy.working_copy and working_copy.empty
    assert working_copy.parents == (second.commit_id,)
    assert repo.bookmark("main").target == first.commit_id
    assert repo.bookmark("missing") is None


def test_file_queries_handle_fileset_metacharacters(sandbox):
    repo = sandbox.init_repo()
    commit = repo.commit("Add notes", {"docs/notes (draft).md": "draft\n", "~backup.txt": "b\n"})

    assert repo.file(commit.commit_id, "docs/notes (draft).md") == "draft\n"
    assert repo.file(commit.commit_id, "~backup.txt") == "b\n"
    assert repo.files(commit.commit_id) == {"docs/notes (draft).md", "~backup.txt"}


def test_setup_is_deterministic(tmp_path, jj):
    commit_ids = []
    for name in ("first", "second"):
        repo = Sandbox.create(tmp_path / name, jj).init_repo()
        commit_ids.append(repo.commit("Initial import", {"README.md": "x\n"}).commit_id)
    assert commit_ids[0] == commit_ids[1]
