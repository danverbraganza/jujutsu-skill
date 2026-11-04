from jj_eval.sandbox import Sandbox


def recording_sandbox(tmp_path):
    """A sandbox whose jj only records its arguments, in jj-args.log."""
    jj = tmp_path / "jj"
    jj.write_text('#!/bin/sh\necho "$@" >> "$(dirname "$0")/jj-args.log"\n')
    jj.chmod(0o755)
    sb = Sandbox(root=tmp_path / "app", jj=jj)
    sb.root.mkdir()
    return sb


def test_scenario_repos_are_created_and_cloned_without_colocation(tmp_path):
    sb = recording_sandbox(tmp_path)

    sb.init_repo()
    sb.clone_origin()

    assert (tmp_path / "jj-args.log").read_text().splitlines() == [
        "git init --no-colocate",
        f"git clone --no-colocate {sb.origin_dir} repo",
    ]


def test_an_interop_scenario_can_opt_in_to_a_colocated_repo(tmp_path):
    sb = recording_sandbox(tmp_path)

    sb.init_repo(colocate=True)

    assert (tmp_path / "jj-args.log").read_text().splitlines() == ["git init --colocate"]
